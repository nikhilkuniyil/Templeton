"""LLM-assisted research manager layered on top of Templeton's deterministic pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .llm import LLMClient
from .models import AgentEnvelope, ResearchRequest, SourcePacket


class LLMResearchManager:
    """Uses an LLM to explain and synthesize evidence-backed research results."""

    INVESTIGATION_SYSTEM_PROMPT = (
        "You are Templeton, an investment research assistant. "
        "Only use the provided evidence-backed context. "
        "Do not invent facts, prices, filings, or news. "
        "If evidence is weak or conflicted, say so explicitly."
    )

    CHAT_SYSTEM_PROMPT = (
        "You are Templeton's conversational research layer. "
        "Answer the user using only the supplied research context. "
        "Do not invent data that is not present in the context."
    )

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def compose_investigation_answer(
        self,
        request: ResearchRequest,
        outputs: dict[str, AgentEnvelope],
    ) -> str:
        return self.compose_investigation_response(request, outputs).text

    def compose_investigation_response(
        self,
        request: ResearchRequest,
        outputs: dict[str, AgentEnvelope],
    ) -> "LLMResponse":  # type: ignore[name-defined]  # noqa: F821
        from .llm import LLMResponse  # local import avoids circular reference at module level
        prompt = self._build_investigation_prompt(request, outputs)
        return self.llm_client.generate(self.INVESTIGATION_SYSTEM_PROMPT, prompt)

    def _build_investigation_prompt(
        self,
        request: ResearchRequest,
        outputs: dict[str, AgentEnvelope],
    ) -> str:
        return (
            f"User question: {request.user_query}\n\n"
            "Structured research context:\n"
            f"{self._context_json(outputs)}\n\n"
            "Write a concise investor-facing memo with:\n"
            "1. Decision\n"
            "2. What changed\n"
            "3. Bull case\n"
            "4. Bear case\n"
            "5. Verification note\n"
            "Use only the supplied context."
        )

    def answer_chat(
        self,
        request: ResearchRequest,
        prior_research: dict[str, AgentEnvelope],
    ) -> str:
        return self.answer_chat_response(request, prior_research).text

    def answer_chat_response(
        self,
        request: ResearchRequest,
        prior_research: dict[str, AgentEnvelope],
    ) -> "LLMResponse":  # type: ignore[name-defined]  # noqa: F821
        prompt = (
            f"User question: {request.user_query}\n\n"
            "Prior research context:\n"
            f"{self._context_json(prior_research)}\n\n"
            "Answer directly and briefly. If the context is insufficient, say so."
        )
        return self.llm_client.generate(self.CHAT_SYSTEM_PROMPT, prompt)

    def _context_json(self, outputs: dict[str, AgentEnvelope]) -> str:
        compact = {
            name: {
                "summary": envelope.summary,
                "confidence": envelope.confidence,
                "payload": envelope.payload,
                "evidence_ids": envelope.evidence_ids,
            }
            for name, envelope in outputs.items()
        }
        return json.dumps(compact, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Agentic manager loop
# ---------------------------------------------------------------------------

@dataclass
class LoopResult:
    """Result of a ManagerLoop run."""

    memo: str
    agents_run: list[str]
    plan_thought: str
    model: str
    provider: str
    outputs: dict[str, AgentEnvelope]
    loop_steps: list[dict[str, Any]] = field(default_factory=list)


class ManagerLoop:
    """Agentic research loop: LLM plans which agents to run, calls them, synthesizes.

    Flow
    ----
    1. *Plan* — ask LLM which subset of analysis agents best answers the query.
    2. *Execute* — run infrastructure agents (router_planner, source_verification)
       then the LLM-selected agents in pipeline order.
    3. *Synthesize* — ask LLM to produce the final investor memo from accumulated outputs.
    """

    # Selectable analysis agents (infrastructure agents are always prepended).
    AGENT_REGISTRY: dict[str, str] = {
        "business_quality": "Business model strength, competitive moat, management quality",
        "financial_quality": "Revenue growth, margins, cash flow, balance sheet health",
        "valuation": "Price multiples, DCF estimates, relative value vs peers",
        "technical_analysis": "Price trends, momentum indicators, support/resistance levels",
        "news_catalyst": "Recent events, earnings results, product launches, macro catalysts",
        "risk": "Key risks, tail events, short-seller concerns, regulatory threats",
        "decision_portfolio_fit": "Final buy/watch/pass decision with thesis and triggers",
        "verifier": "Checks stale data, contradictions, and support gaps before finalizing confidence",
        "synthesizer": "Comprehensive memo combining outputs from all other agents",
    }

    # Pipeline order for selectable agents (mirrors INVESTIGATION_AGENT_ORDER minus infra).
    _PIPELINE_ORDER = [
        "business_quality",
        "financial_quality",
        "valuation",
        "technical_analysis",
        "news_catalyst",
        "risk",
        "decision_portfolio_fit",
        "verifier",
        "synthesizer",
    ]

    _PLANNER_SYSTEM = (
        "You are Templeton's research director. "
        "Given a user query, select the minimum set of analysis agents needed to answer it well. "
        "Always include 'decision_portfolio_fit' and 'synthesizer'. "
        "Respond ONLY with valid JSON — no markdown fences, no prose outside the JSON object."
    )

    _SYNTHESIS_SYSTEM = (
        "You are Templeton, an investment research assistant. "
        "Only use the provided evidence-backed context. "
        "Do not invent facts, prices, filings, or news. "
        "If evidence is weak or conflicted, say so explicitly."
    )

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def run(
        self,
        request: ResearchRequest,
        agent_executor: Callable[..., AgentEnvelope],
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope] | None = None,
        run_dir: Path | None = None,
        run_store: Any | None = None,
    ) -> LoopResult:
        """Plan → execute → synthesize.  Returns a LoopResult with the memo and metadata."""
        prior_outputs = prior_outputs or {}

        # ── 1. Plan ──────────────────────────────────────────────────────────
        agent_list = "\n".join(
            f"- {name}: {desc}" for name, desc in self.AGENT_REGISTRY.items()
        )
        plan_prompt = (
            f"User query: {request.user_query}\n\n"
            f"Available analysis agents:\n{agent_list}\n\n"
            'Respond with JSON: {"thought": "<one sentence>", "agents": ["<name>", ...]}'
        )
        plan_response = self.llm_client.generate(self._PLANNER_SYSTEM, plan_prompt)

        try:
            plan = json.loads(plan_response.text)
        except json.JSONDecodeError:
            # Fall back to running all agents if LLM response is not clean JSON.
            plan = {"thought": "fallback: LLM plan parse failed", "agents": list(self.AGENT_REGISTRY)}

        requested = set(plan.get("agents", list(self.AGENT_REGISTRY)))
        plan_thought = plan.get("thought", "")

        # Always include decision, verification, and synthesis.
        requested.update({"decision_portfolio_fit", "verifier", "synthesizer"})

        # ── 2. Execute ────────────────────────────────────────────────────────
        # Infrastructure agents first, then selected analysis agents in pipeline order.
        ordered: list[str] = ["router_planner", "source_verification"]
        for name in self._PIPELINE_ORDER:
            if name in requested:
                ordered.append(name)

        outputs: dict[str, AgentEnvelope] = dict(prior_outputs)
        loop_steps: list[dict[str, Any]] = [
            {"step": "plan", "thought": plan_thought, "agents_selected": list(requested)}
        ]

        for agent_name in ordered:
            try:
                envelope = agent_executor(
                    agent_name=agent_name,
                    request=request,
                    prior_outputs=outputs,
                    source_packets=source_packets,
                )
            except Exception as exc:  # noqa: BLE001
                loop_steps.append({"step": "agent_error", "agent": agent_name, "error": str(exc)})
                continue

            outputs[agent_name] = envelope
            loop_steps.append(
                {
                    "step": "agent_output",
                    "agent": agent_name,
                    "summary": envelope.summary,
                    "confidence": envelope.confidence,
                }
            )
            if run_store is not None and run_dir is not None:
                run_store.record_agent_output(run_dir, envelope)

        # ── 3. Synthesize ─────────────────────────────────────────────────────
        synthesis_prompt = (
            f"User question: {request.user_query}\n\n"
            "Structured research context (from selected agents):\n"
            f"{self._context_json(outputs)}\n\n"
            "Write a concise investor-facing memo with:\n"
            "1. Decision\n"
            "2. What changed\n"
            "3. Bull case\n"
            "4. Bear case\n"
            "5. Verification note\n"
            "Use only the supplied context."
        )
        synthesis_response = self.llm_client.generate(self._SYNTHESIS_SYSTEM, synthesis_prompt)
        memo = synthesis_response.text

        if run_store is not None and run_dir is not None:
            run_store.record_llm_memo(
                run_dir,
                memo,
                model=synthesis_response.model,
                provider=synthesis_response.provider,
                mode="agentic_loop",
            )

        return LoopResult(
            memo=memo,
            agents_run=ordered,
            plan_thought=plan_thought,
            model=synthesis_response.model,
            provider=synthesis_response.provider,
            outputs=outputs,
            loop_steps=loop_steps,
        )

    def _context_json(self, outputs: dict[str, AgentEnvelope]) -> str:
        compact = {
            name: {
                "summary": envelope.summary,
                "confidence": envelope.confidence,
                "payload": envelope.payload,
                "evidence_ids": envelope.evidence_ids,
            }
            for name, envelope in outputs.items()
        }
        return json.dumps(compact, indent=2, sort_keys=True)
