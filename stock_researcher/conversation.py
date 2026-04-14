"""Conversational interface over evidence and investigation workflows."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AgentEnvelope, ResearchRequest
from .orchestrator import InvestigationOrchestrator


@dataclass(slots=True)
class ConversationResult:
    answer: str
    envelope: AgentEnvelope


class ConversationalInterface:
    """Answers simple questions from prior evidence or requests a refresh."""

    TIME_SENSITIVE_TERMS = {
        "today",
        "current",
        "latest",
        "recent",
        "right now",
        "news",
        "price",
        "still worth buying",
    }

    def respond(
        self,
        request: ResearchRequest,
        prior_research: dict[str, AgentEnvelope] | None = None,
    ) -> ConversationResult:
        prior_research = prior_research or {}
        needs_fresh_data = self._needs_fresh_data(request.user_query)
        ticker = request.tickers[0] if request.tickers else None

        if prior_research and not needs_fresh_data:
            answer = self._answer_from_prior_research(request, prior_research)
            action = None
            used_existing_research = True
        else:
            answer = (
                "This question needs fresh retrieval or deeper analysis before I should answer confidently."
            )
            action = "run_investigation_refresh" if ticker else "clarify_target"
            used_existing_research = bool(prior_research)

        envelope = AgentEnvelope(
            agent_name="conversational_interface",
            ticker=ticker,
            analysis_mode="conversation",
            summary="Generated conversational response.",
            confidence="medium" if not needs_fresh_data and prior_research else "low",
            key_points=[f"Used existing research: {used_existing_research}"],
            evidence_ids=self._collect_evidence_ids(prior_research),
            payload={
                "agent_name": "conversational_interface",
                "summary": "Answered the user in conversational mode.",
                "response_type": "direct_answer" if action is None else "workflow_handoff",
                "answer": answer,
                "used_existing_research": used_existing_research,
                "needs_fresh_data": needs_fresh_data,
                "recommended_next_action": action,
                "evidence_ids": self._collect_evidence_ids(prior_research),
                "confidence": "medium" if action is None else "low",
            },
        )
        return ConversationResult(answer=answer, envelope=envelope)

    def refresh_investigation(
        self,
        request: ResearchRequest,
        orchestrator: InvestigationOrchestrator,
        agent_executor,
    ):
        refresh_request = ResearchRequest(
            request_id=request.request_id,
            user_query=request.user_query,
            mode="investigation",
            tickers=request.tickers,
            time_horizon=request.time_horizon,
            objective=request.objective,
            risk_tolerance=request.risk_tolerance,
            portfolio_context_available=request.portfolio_context_available,
            requested_at=request.requested_at,
        )
        return orchestrator.run(refresh_request, agent_executor=agent_executor)

    def _needs_fresh_data(self, query: str) -> bool:
        lowered = query.lower()
        return any(term in lowered for term in self.TIME_SENSITIVE_TERMS)

    def _answer_from_prior_research(
        self,
        request: ResearchRequest,
        prior_research: dict[str, AgentEnvelope],
    ) -> str:
        decision = prior_research.get("decision_portfolio_fit")
        source_verification = prior_research.get("source_verification")
        if decision is not None:
            decision_label = str(decision.payload.get("decision", "watch")).upper()
            summary = decision.summary
            freshness = (
                source_verification.payload.get("freshness_status", "unknown")
                if source_verification is not None
                else "unknown"
            )
            return f"Prior research leans {decision_label}. {summary} Source freshness: {freshness}."
        synth = prior_research.get("synthesizer")
        if synth is not None:
            return synth.summary
        return f"I have prior research context for {', '.join(request.tickers)}, but not a final decision yet."

    def _collect_evidence_ids(self, prior_research: dict[str, AgentEnvelope]) -> list[str]:
        evidence_ids: list[str] = []
        for envelope in prior_research.values():
            evidence_ids.extend(envelope.evidence_ids)
        return sorted(set(evidence_ids))
