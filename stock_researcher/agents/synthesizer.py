"""Concrete synthesizer implementation."""

from __future__ import annotations

from ..run_store import LocalRunStore
from ..models import AgentEnvelope, ResearchRequest, SourcePacket


class SynthesizerAgent:
    """Converts prior outputs into a concise final memo."""

    def __init__(self, run_store: LocalRunStore | None = None) -> None:
        self.run_store = run_store

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
        previous_outputs = self.run_store.load_latest_outputs(ticker) if self.run_store is not None else {}
        what_changed = self._what_changed(
            current_decision=decision,
            current_valuation=valuation,
            current_risk=risk,
            current_verifier=verifier,
            previous_outputs=previous_outputs,
        )

        memo_sections = {
            "thesis": decision.summary,
            "decision": f"{decision_label} with {final_confidence.upper()} confidence. Source freshness: {freshness}.",
            "bull_case": bull_case,
            "bear_case": bear_case,
            "what_changed": what_changed,
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
            "what_changed": self._evidence_for(decision, valuation, risk, verifier),
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
                memo_sections["what_changed"],
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

    def _what_changed(
        self,
        current_decision: AgentEnvelope,
        current_valuation: AgentEnvelope | None,
        current_risk: AgentEnvelope | None,
        current_verifier: AgentEnvelope | None,
        previous_outputs: dict[str, AgentEnvelope],
    ) -> str:
        if not previous_outputs:
            return "No prior memo available for comparison."

        changes: list[str] = []
        previous_decision = previous_outputs.get("decision_portfolio_fit")
        previous_valuation = previous_outputs.get("valuation")
        previous_risk = previous_outputs.get("risk")
        previous_verifier = previous_outputs.get("verifier")

        current_decision_label = str(current_decision.payload.get("decision", "watch"))
        previous_decision_label = (
            str(previous_decision.payload.get("decision", "watch"))
            if previous_decision is not None
            else None
        )
        if previous_decision_label is not None and previous_decision_label != current_decision_label:
            changes.append(
                f"Decision changed from {previous_decision_label.upper()} to {current_decision_label.upper()}."
            )

        current_confidence = (
            str(current_verifier.payload.get("adjusted_confidence"))
            if current_verifier is not None
            else str(current_decision.payload.get("confidence", current_decision.confidence))
        )
        previous_confidence = None
        if previous_verifier is not None:
            previous_confidence = str(previous_verifier.payload.get("adjusted_confidence"))
        elif previous_decision is not None:
            previous_confidence = str(previous_decision.payload.get("confidence", previous_decision.confidence))
        if previous_confidence is not None and previous_confidence != current_confidence:
            changes.append(f"Confidence changed from {previous_confidence.upper()} to {current_confidence.upper()}.")

        current_valuation_label = (
            str(current_valuation.payload.get("valuation_label", "unknown"))
            if current_valuation is not None
            else "unknown"
        )
        previous_valuation_label = (
            str(previous_valuation.payload.get("valuation_label", "unknown"))
            if previous_valuation is not None
            else None
        )
        if previous_valuation_label is not None and previous_valuation_label != current_valuation_label:
            changes.append(f"Valuation view changed from {previous_valuation_label} to {current_valuation_label}.")

        current_top_risk = self._top_risk(current_risk)
        previous_top_risk = self._top_risk(previous_risk)
        if previous_top_risk and current_top_risk and previous_top_risk != current_top_risk:
            changes.append(f"Top risk changed from '{previous_top_risk}' to '{current_top_risk}'.")

        if not changes:
            return "No material thesis change versus the latest saved memo."
        return " ".join(changes[:4])

    def _top_risk(self, envelope: AgentEnvelope | None) -> str | None:
        if envelope is None:
            return None
        for item in envelope.payload.get("core_risks", []):
            if isinstance(item, dict):
                risk = str(item.get("risk", "")).strip()
                if risk:
                    return risk
        return None
