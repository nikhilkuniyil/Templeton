"""Rule-based verifier for checking support, freshness, and contradictions."""

from __future__ import annotations

from ..models import AgentEnvelope, ResearchRequest, SourcePacket


class VerifierAgent:
    """Checks whether the current research outputs justify the conclusion."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        decision = prior_outputs.get("decision_portfolio_fit")
        source = prior_outputs.get("source_verification")
        valuation = prior_outputs.get("valuation")
        technical = prior_outputs.get("technical_analysis")
        financial = prior_outputs.get("financial_quality")
        business = prior_outputs.get("business_quality")
        risk = prior_outputs.get("risk")

        stale_data = source is not None and source.payload.get("freshness_status") == "stale"
        contradictions: list[str] = []
        unsupported_claims: list[str] = []
        missing_evidence: list[str] = []
        warnings: list[str] = []

        evidence_ids: list[str] = []
        for name in (
            "source_verification",
            "business_quality",
            "financial_quality",
            "valuation",
            "technical_analysis",
            "risk",
            "decision_portfolio_fit",
        ):
            envelope = prior_outputs.get(name)
            if envelope is not None:
                evidence_ids.extend(envelope.evidence_ids)
        evidence_ids = list(dict.fromkeys(evidence_ids))

        decision_label = decision.payload.get("decision", "watch") if decision is not None else "watch"
        decision_confidence = decision.payload.get("confidence", "low") if decision is not None else "low"
        valuation_label = valuation.payload.get("valuation_label", "unknown") if valuation is not None else "unknown"
        entry_quality = technical.payload.get("entry_quality", "unknown") if technical is not None else "unknown"
        business_rating = business.payload.get("durability_rating", "low") if business is not None else "low"
        financial_rating = (
            financial.payload.get("overall_quality_rating", "low") if financial is not None else "low"
        )
        top_risks = []
        if risk is not None:
            top_risks = [
                str(item.get("risk", ""))
                for item in risk.payload.get("core_risks", [])
                if isinstance(item, dict)
            ]

        if not evidence_ids:
            missing_evidence.append("No evidence ids were attached to the research outputs.")
        if source is not None:
            missing_evidence.extend(str(item) for item in source.payload.get("missing_data", []))
        if stale_data:
            warnings.append("Source freshness is stale.")
        if decision_label == "buy" and valuation_label in {"expensive", "fair_to_expensive"}:
            contradictions.append("Decision is BUY while valuation is not supportive.")
        if decision_label == "buy" and entry_quality == "extended":
            contradictions.append("Decision is BUY while technical entry is extended.")
        if decision_label == "buy" and (business_rating != "high" or financial_rating != "high"):
            unsupported_claims.append("BUY decision is not supported by strong business and financial quality.")
        if decision_label == "pass" and business_rating == "high" and financial_rating == "high" and valuation_label in {"cheap", "fair"}:
            contradictions.append("Decision is PASS despite strong quality and supportive valuation.")
        if risk is not None and not top_risks:
            missing_evidence.append("Risk agent did not provide actionable core risks.")
        if valuation is not None and valuation_label == "unknown":
            missing_evidence.append("Valuation view is unknown.")

        verifier_status = "pass"
        adjusted_confidence = decision_confidence
        recommended_action = "accept"

        if stale_data or missing_evidence:
            verifier_status = "review"
            recommended_action = "downgrade_confidence"
            adjusted_confidence = self._downgrade(adjusted_confidence)
        if contradictions or unsupported_claims:
            verifier_status = "fail"
            recommended_action = "repair_or_downgrade"
            adjusted_confidence = "low"

        summary = self._summary(
            ticker=ticker,
            verifier_status=verifier_status,
            contradictions=contradictions,
            stale_data=stale_data,
            missing_evidence=missing_evidence,
        )

        return AgentEnvelope(
            agent_name="verifier",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=adjusted_confidence,
            key_points=[
                f"Verifier status: {verifier_status}",
                f"Contradictions found: {len(contradictions)}",
                f"Missing evidence flags: {len(missing_evidence)}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[],
            payload={
                "agent_name": "verifier",
                "ticker": ticker,
                "summary": summary,
                "verifier_status": verifier_status,
                "adjusted_confidence": adjusted_confidence,
                "stale_data": stale_data,
                "contradictions": contradictions,
                "unsupported_claims": unsupported_claims,
                "missing_evidence": missing_evidence,
                "warnings": warnings,
                "recommended_action": recommended_action,
                "evidence_ids": evidence_ids,
                "open_questions": [],
            },
        )

    def _summary(
        self,
        ticker: str,
        verifier_status: str,
        contradictions: list[str],
        stale_data: bool,
        missing_evidence: list[str],
    ) -> str:
        if verifier_status == "pass":
            return f"{ticker} verification passed with no material support gaps."
        issues: list[str] = []
        if stale_data:
            issues.append("stale data")
        if contradictions:
            issues.append(f"{len(contradictions)} contradiction(s)")
        if missing_evidence:
            issues.append(f"{len(missing_evidence)} evidence gap(s)")
        joined = ", ".join(issues) if issues else "support concerns"
        return f"{ticker} verification flagged {joined}."

    def _downgrade(self, confidence: str) -> str:
        if confidence == "high":
            return "medium"
        return "low"
