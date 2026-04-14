"""Concrete business quality agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class BusinessQualityAgent:
    """Builds a basic business-quality view from source metadata."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        primary_sources = [*packet.filings, *packet.market_data, *packet.news]

        revenue_drivers = self._collect_metadata_values(primary_sources, "revenue_drivers")
        competitive_advantages = self._collect_metadata_values(primary_sources, "competitive_advantages")
        vulnerabilities = self._collect_metadata_values(primary_sources, "vulnerabilities")
        business_model = self._first_metadata_value(primary_sources, "business_model", "Business model not extracted yet.")

        if not competitive_advantages and packet.filings:
            competitive_advantages = ["Primary company disclosures available"]
        if not vulnerabilities and packet.news:
            vulnerabilities = ["Needs deeper review of recent developments"]

        evidence_ids = []
        if "source_verification" in prior_outputs:
            evidence_ids = list(prior_outputs["source_verification"].evidence_ids[:5])

        summary = self._build_summary(
            ticker=ticker,
            business_model=business_model,
            competitive_advantages=competitive_advantages,
            vulnerabilities=vulnerabilities,
        )
        durability_rating = self._durability_rating(competitive_advantages, vulnerabilities)

        return AgentEnvelope(
            agent_name="business_quality",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence="medium" if primary_sources else "low",
            key_points=[
                f"Business model: {business_model}",
                f"Competitive advantages identified: {len(competitive_advantages)}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[] if primary_sources else ["No primary sources available for business-quality review."],
            payload={
                "agent_name": "business_quality",
                "ticker": ticker,
                "summary": summary,
                "business_model": business_model,
                "revenue_drivers": revenue_drivers,
                "competitive_advantages": competitive_advantages,
                "vulnerabilities": vulnerabilities,
                "durability_rating": durability_rating,
                "evidence_ids": evidence_ids,
                "confidence": "medium" if primary_sources else "low",
                "open_questions": [] if primary_sources else ["No primary sources available for business-quality review."],
            },
        )

    def _collect_metadata_values(self, documents: Iterable[SourceDocument], field_name: str) -> list[str]:
        values: list[str] = []
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
            elif isinstance(raw, str):
                values.append(raw)
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped

    def _first_metadata_value(
        self,
        documents: Iterable[SourceDocument],
        field_name: str,
        default: str,
    ) -> str:
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, str) and raw:
                return raw
        return default

    def _durability_rating(self, competitive_advantages: list[str], vulnerabilities: list[str]) -> str:
        if len(competitive_advantages) >= 2 and len(vulnerabilities) <= 1:
            return "high"
        if competitive_advantages:
            return "medium"
        return "low"

    def _build_summary(
        self,
        ticker: str,
        business_model: str,
        competitive_advantages: list[str],
        vulnerabilities: list[str],
    ) -> str:
        if business_model == "Business model not extracted yet.":
            return f"{ticker} business quality is not fully characterized yet."
        advantages = ", ".join(competitive_advantages[:2]) if competitive_advantages else "limited identified advantages"
        risks = ", ".join(vulnerabilities[:2]) if vulnerabilities else "no major vulnerabilities surfaced yet"
        return f"{ticker} operates as: {business_model}. Key strengths: {advantages}. Main vulnerabilities: {risks}."
