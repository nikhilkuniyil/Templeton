"""LLM-assisted research manager layered on top of Templeton's deterministic pipeline."""

from __future__ import annotations

import json

from .llm import LLMClient
from .models import AgentEnvelope, ResearchRequest


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
        prompt = (
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
        return self.llm_client.generate(self.INVESTIGATION_SYSTEM_PROMPT, prompt).text

    def answer_chat(
        self,
        request: ResearchRequest,
        prior_research: dict[str, AgentEnvelope],
    ) -> str:
        prompt = (
            f"User question: {request.user_query}\n\n"
            "Prior research context:\n"
            f"{self._context_json(prior_research)}\n\n"
            "Answer directly and briefly. If the context is insufficient, say so."
        )
        return self.llm_client.generate(self.CHAT_SYSTEM_PROMPT, prompt).text

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
