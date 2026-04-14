"""Concrete synthesizer implementation."""

from __future__ import annotations

from ..models import AgentEnvelope, ResearchRequest, SourcePacket


class SynthesizerAgent:
    """Converts prior outputs into a concise final memo."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        decision = prior_outputs["decision_portfolio_fit"]
        business = prior_outputs.get("business_quality")
        financial = prior_outputs.get("financial_quality")
        valuation = prior_outputs.get("valuation")
        news = prior_outputs.get("news_catalyst")
        risk = prior_outputs.get("risk")

        memo_sections = {
            "thesis": decision.summary,
            "business_quality": business.summary if business is not None else "Unavailable.",
            "financial_quality": financial.summary if financial is not None else "Unavailable.",
            "valuation": valuation.summary if valuation is not None else "Unavailable.",
            "catalysts": news.summary if news is not None else "Unavailable.",
            "risks": risk.summary if risk is not None else "Unavailable.",
            "monitoring": ", ".join(risk.payload.get("monitoring_indicators", [])) if risk is not None else "",
        }
        evidence_ids: list[str] = []
        for envelope in prior_outputs.values():
            evidence_ids.extend(envelope.evidence_ids)
        evidence_ids = list(dict.fromkeys(evidence_ids))
        summary = f"{ticker} memo complete. Current stance: {decision.payload.get('decision', 'watch').upper()}."

        return AgentEnvelope(
            agent_name="synthesizer",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=decision.confidence,
            key_points=[
                memo_sections["thesis"],
                memo_sections["valuation"],
            ],
            evidence_ids=evidence_ids,
            open_questions=[],
            payload={
                "agent_name": "synthesizer",
                "ticker": ticker,
                "summary": summary,
                "decision": decision.payload.get("decision", "watch"),
                "confidence": decision.confidence,
                "memo_sections": memo_sections,
                "evidence_ids": evidence_ids,
                "open_questions": [],
            },
        )
