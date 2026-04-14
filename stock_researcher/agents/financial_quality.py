"""Concrete financial quality agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class FinancialQualityAgent:
    """Builds a basic financial-quality view from source metadata."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        docs = [*packet.filings, *packet.market_data, *packet.news]

        growth_profile = self._first_object(docs, "growth_profile", {})
        margin_profile = self._first_object(docs, "margin_profile", {})
        cash_flow_profile = self._first_object(docs, "cash_flow_profile", {})
        balance_sheet_profile = self._first_object(docs, "balance_sheet_profile", {})
        capital_allocation = self._first_object(docs, "capital_allocation", {})
        overall_quality_rating = self._quality_rating(
            growth_profile,
            margin_profile,
            cash_flow_profile,
            balance_sheet_profile,
        )

        evidence_ids = self._evidence_ids(prior_outputs)
        summary = self._summary(
            ticker=ticker,
            growth_profile=growth_profile,
            margin_profile=margin_profile,
            cash_flow_profile=cash_flow_profile,
            balance_sheet_profile=balance_sheet_profile,
        )
        confidence = "medium" if docs else "low"

        return AgentEnvelope(
            agent_name="financial_quality",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[
                f"Revenue growth trend: {growth_profile.get('revenue_growth_trend', 'unknown')}",
                f"Free cash flow quality: {cash_flow_profile.get('free_cash_flow_quality', 'unknown')}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[] if docs else ["No source metadata available for financial-quality review."],
            payload={
                "agent_name": "financial_quality",
                "ticker": ticker,
                "summary": summary,
                "growth_profile": growth_profile,
                "margin_profile": margin_profile,
                "cash_flow_profile": cash_flow_profile,
                "balance_sheet_profile": balance_sheet_profile,
                "capital_allocation": capital_allocation,
                "overall_quality_rating": overall_quality_rating,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "open_questions": [] if docs else ["No source metadata available for financial-quality review."],
            },
        )

    def _first_object(
        self,
        documents: Iterable[SourceDocument],
        field_name: str,
        default: dict,
    ) -> dict:
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, dict):
                return raw
        return default

    def _quality_rating(
        self,
        growth_profile: dict,
        margin_profile: dict,
        cash_flow_profile: dict,
        balance_sheet_profile: dict,
    ) -> str:
        positive = 0
        if growth_profile.get("revenue_growth_trend") in {"positive", "strong"}:
            positive += 1
        if margin_profile.get("gross_margin_trend") in {"stable", "stable_to_up", "up"}:
            positive += 1
        if cash_flow_profile.get("free_cash_flow_quality") in {"strong", "healthy"}:
            positive += 1
        if balance_sheet_profile.get("debt_risk") in {"low"}:
            positive += 1
        if positive >= 4:
            return "high"
        if positive >= 2:
            return "medium"
        return "low"

    def _summary(
        self,
        ticker: str,
        growth_profile: dict,
        margin_profile: dict,
        cash_flow_profile: dict,
        balance_sheet_profile: dict,
    ) -> str:
        return (
            f"{ticker} shows {growth_profile.get('revenue_growth_trend', 'unclear')} growth, "
            f"{margin_profile.get('gross_margin_trend', 'unclear')} gross-margin trend, "
            f"{cash_flow_profile.get('free_cash_flow_quality', 'unclear')} free cash flow quality, "
            f"and {balance_sheet_profile.get('debt_risk', 'unclear')} debt risk."
        )

    def _evidence_ids(self, prior_outputs: dict[str, AgentEnvelope]) -> list[str]:
        source = prior_outputs.get("source_verification")
        return list(source.evidence_ids[:5]) if source is not None else []
