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
        technical = prior_outputs.get("technical_analysis")
        valuation = prior_outputs.get("valuation")
        news = prior_outputs.get("news_catalyst")
        risk = prior_outputs.get("risk")
        verifier = prior_outputs.get("verifier")
        source = prior_outputs.get("source_verification")

        decision_label = decision.payload.get("decision", "watch").upper()
        final_confidence = (
            verifier.payload.get("adjusted_confidence", decision.confidence)
            if verifier is not None
            else decision.confidence
        )

        bull_case = self._join_points(
            [
                self._first_reason(decision, "Business quality is"),
                business.summary if business is not None else None,
                financial.summary if financial is not None else None,
                news.summary if news is not None else None,
            ]
        )
        bear_case = self._join_points(
            [
                risk.summary if risk is not None else None,
                valuation.summary if valuation is not None else None,
                verifier.summary if verifier is not None and verifier.payload.get("verifier_status") != "pass" else None,
            ]
        )
        monitoring = ", ".join(risk.payload.get("monitoring_indicators", [])) if risk is not None else "No monitoring indicators."
        freshness = source.payload.get("freshness_status", "unknown") if source is not None else "unknown"

        memo_sections = {
            "thesis": decision.summary,
            "decision": f"{decision_label} with {final_confidence.upper()} confidence. Source freshness: {freshness}.",
            "bull_case": bull_case,
            "bear_case": bear_case,
            "business_quality": business.summary if business is not None else "Unavailable.",
            "financial_quality": financial.summary if financial is not None else "Unavailable.",
            "valuation": valuation.summary if valuation is not None else "Unavailable.",
            "technical": technical.summary if technical is not None else "Unavailable.",
            "catalysts": news.summary if news is not None else "Unavailable.",
            "risks": risk.summary if risk is not None else "Unavailable.",
            "monitoring": monitoring,
            "verification": verifier.summary if verifier is not None else "No verifier output.",
        }
        evidence_map = {
            "thesis": self._evidence_for(decision),
            "decision": self._evidence_for(decision, verifier),
            "bull_case": self._evidence_for(business, financial, news),
            "bear_case": self._evidence_for(risk, valuation, verifier),
            "business_quality": self._evidence_for(business),
            "financial_quality": self._evidence_for(financial),
            "valuation": self._evidence_for(valuation),
            "technical": self._evidence_for(technical),
            "catalysts": self._evidence_for(news),
            "risks": self._evidence_for(risk),
            "monitoring": self._evidence_for(risk),
            "verification": self._evidence_for(verifier),
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
            confidence=final_confidence,
            key_points=[
                memo_sections["thesis"],
                memo_sections["valuation"],
                memo_sections["verification"],
            ],
            evidence_ids=evidence_ids,
            open_questions=[],
            payload={
                "agent_name": "synthesizer",
                "ticker": ticker,
                "summary": summary,
                "decision": decision.payload.get("decision", "watch"),
                "confidence": final_confidence,
                "memo_sections": memo_sections,
                "evidence_map": evidence_map,
                "evidence_ids": evidence_ids,
                "open_questions": [],
            },
        )

    def _evidence_for(self, *envelopes: AgentEnvelope | None) -> list[str]:
        evidence_ids: list[str] = []
        for envelope in envelopes:
            if envelope is None:
                continue
            evidence_ids.extend(envelope.evidence_ids)
        return list(dict.fromkeys(evidence_ids))

    def _first_reason(self, envelope: AgentEnvelope, prefix: str) -> str | None:
        for reason in envelope.payload.get("key_reasons", []):
            if str(reason).startswith(prefix):
                return str(reason)
        return None

    def _join_points(self, parts: list[str | None]) -> str:
        values = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
        if not values:
            return "Unavailable."
        return " ".join(values)
