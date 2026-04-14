"""Concrete source verification agent implementation."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from ..models import AgentEnvelope, Evidence, ResearchRequest, SourceDocument, SourcePacket


class SourceVerificationAgent:
    """Normalizes connector output into a validated source-verification payload."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
    ) -> AgentEnvelope:
        tickers = request.tickers
        sources_used: list[dict[str, str]] = []
        evidence: list[Evidence] = []
        missing_data: list[str] = []
        conflicts_found: list[str] = []
        freshness_status = "fresh"

        for ticker in tickers:
            packet = source_packets.get(ticker)
            if packet is None:
                missing_data.append(f"No source packet available for {ticker}")
                freshness_status = "stale"
                continue

            packet_sources = [*packet.filings, *packet.market_data, *packet.news]
            if not packet_sources:
                missing_data.append(f"No sources found for {ticker}")
                freshness_status = "stale"
                continue

            sources_used.extend(self._serialize_sources(packet_sources))
            evidence.extend(self._build_evidence(packet))
            packet_freshness = self._freshness_for_packet(packet_sources)
            if packet_freshness == "stale":
                freshness_status = "stale"
            elif packet_freshness == "mixed" and freshness_status == "fresh":
                freshness_status = "mixed"

        summary = self._build_summary(tickers=tickers, sources_count=len(sources_used), missing_data=missing_data)
        confidence = "high" if sources_used and not missing_data else "medium"

        return AgentEnvelope(
            agent_name="source_verification",
            ticker=tickers[0] if len(tickers) == 1 else None,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[
                f"Collected {len(sources_used)} source documents across {len(tickers)} ticker(s).",
                f"Generated {len(evidence)} evidence objects from source metadata.",
            ],
            evidence_ids=[item.evidence_id for item in evidence],
            open_questions=missing_data,
            sources_used=sources_used,
            payload={
                "agent_name": "source_verification",
                "summary": summary,
                "tickers": tickers,
                "sources_used": sources_used,
                "evidence_ids": [item.evidence_id for item in evidence],
                "freshness_status": freshness_status,
                "missing_data": missing_data,
                "conflicts_found": conflicts_found,
                "confidence": confidence,
            },
        )

    def _serialize_sources(self, documents: Iterable[SourceDocument]) -> list[dict[str, str]]:
        return [
            {
                "source_name": document.source_name,
                "source_type": document.source_type,
                "published_at": document.published_at,
                "retrieved_at": document.retrieved_at,
            }
            for document in documents
        ]

    def _build_evidence(self, packet: SourcePacket) -> list[Evidence]:
        evidence: list[Evidence] = list(packet.evidence)
        if evidence:
            return evidence

        for index, document in enumerate([*packet.filings, *packet.market_data, *packet.news], start=1):
            evidence.append(
                Evidence(
                    evidence_id=f"{packet.ticker.lower()}_ev_{index:03d}",
                    ticker=packet.ticker,
                    claim=f"Source available: {document.source_name}",
                    as_of_date=document.published_at[:10],
                    source_name=document.source_name,
                    source_type=document.source_type,
                    source_url=document.source_url,
                    published_at=document.published_at,
                    retrieved_at=document.retrieved_at,
                    claim_scope=self._claim_scope(document.source_type),
                    confidence="medium",
                )
            )
        return evidence

    def _claim_scope(self, source_type: str) -> str:
        if source_type in {"company_filing_or_release", "investor_relations"}:
            return "primary_source"
        if source_type == "market_data":
            return "market_data"
        if source_type == "news":
            return "news"
        return "general"

    def _freshness_for_packet(self, documents: Iterable[SourceDocument]) -> str:
        freshness_levels = {self._freshness_for_document(document) for document in documents}
        if not freshness_levels:
            return "stale"
        if freshness_levels == {"fresh"}:
            return "fresh"
        if "stale" in freshness_levels:
            return "stale"
        return "mixed"

    def _freshness_for_document(self, document: SourceDocument) -> str:
        try:
            retrieved_at = datetime.fromisoformat(document.retrieved_at.replace("Z", "+00:00"))
        except ValueError:
            return "stale"
        age_days = (datetime.now().astimezone() - retrieved_at.astimezone()).days
        return "fresh" if age_days <= 14 else "mixed" if age_days <= 45 else "stale"

    def _build_summary(self, tickers: list[str], sources_count: int, missing_data: list[str]) -> str:
        if missing_data and sources_count == 0:
            return f"No usable sources collected for {', '.join(tickers)}."
        if missing_data:
            return f"Collected {sources_count} sources, but some data is missing for {', '.join(tickers)}."
        return f"Collected {sources_count} source documents for {', '.join(tickers)}."
