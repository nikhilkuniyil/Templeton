"""Concrete decision / portfolio-fit agent implementation."""

from __future__ import annotations

from ..models import AgentEnvelope, ResearchRequest, SourcePacket


class DecisionPortfolioFitAgent:
    """Produces a simple Buy / Watch / Pass based on upstream agent outputs."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        business = prior_outputs.get("business_quality")
        financial = prior_outputs.get("financial_quality")
        valuation = prior_outputs.get("valuation")
        risk = prior_outputs.get("risk")
        source_verification = prior_outputs.get("source_verification")

        business_rating = business.payload.get("durability_rating") if business is not None else "low"
        financial_rating = financial.payload.get("overall_quality_rating") if financial is not None else "low"
        quality_high = business_rating == "high" and financial_rating == "high"
        quality_supported = business_rating in {"medium", "high"} and financial_rating in {"medium", "high"}
        valuation_label = valuation.payload.get("valuation_label") if valuation is not None else "unknown"
        freshness = source_verification.payload.get("freshness_status") if source_verification is not None else "unknown"
        top_risk = ""
        if risk is not None and risk.payload.get("core_risks"):
            top_risk = risk.payload["core_risks"][0].get("risk", "")

        if freshness == "stale":
            decision = "watch"
            confidence = "low"
            reasons = ["Source freshness is stale, so a firm decision would be weak."]
        elif quality_high and valuation_label in {"cheap", "fair"}:
            decision = "buy"
            confidence = "medium"
            reasons = ["Business quality is strong.", "Financial quality is strong.", "Valuation looks acceptable."]
        elif quality_high:
            decision = "watch"
            confidence = "medium"
            reasons = ["Business quality is strong.", "Financial quality is strong.", "Valuation leaves less room for error."]
        elif quality_supported and valuation_label in {"fair_to_expensive", "expensive", "unknown"}:
            decision = "watch"
            confidence = "medium" if valuation_label != "unknown" else "low"
            reasons = [
                "Source coverage is good enough to support monitoring.",
                "Underlying quality looks at least reasonable from current evidence.",
                "Valuation or incomplete extraction keeps this out of Buy for now.",
            ]
        else:
            decision = "pass"
            confidence = "low"
            reasons = ["The current evidence base is not strong enough to justify a buy decision."]

        if top_risk:
            reasons.append(f"Top risk: {top_risk}.")

        summary = f"{ticker} is currently rated {decision.upper()} based on quality, valuation, and risk balance."
        evidence_ids = []
        for name in ("business_quality", "financial_quality", "valuation", "risk"):
            envelope = prior_outputs.get(name)
            if envelope is not None:
                evidence_ids.extend(envelope.evidence_ids)
        evidence_ids = list(dict.fromkeys(evidence_ids))

        return AgentEnvelope(
            agent_name="decision_portfolio_fit",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=reasons[:3],
            evidence_ids=evidence_ids,
            open_questions=[],
            payload={
                "agent_name": "decision_portfolio_fit",
                "ticker": ticker,
                "summary": summary,
                "decision": decision,
                "confidence": confidence,
                "best_fit": "long_term_hold" if request.time_horizon == "long_term" else "starter_position",
                "portfolio_flags": [],
                "key_reasons": reasons,
                "invalidation_triggers": [top_risk] if top_risk else [],
                "evidence_ids": evidence_ids,
                "open_questions": [],
            },
        )
