"""Concrete technical analysis agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class TechnicalAnalysisAgent:
    """Builds a simple technical view from market-data metadata."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        docs = [*packet.market_data, *packet.news]
        technical = self._first_object(docs, "technical_analysis", {})

        trend = str(technical.get("trend", "unknown"))
        momentum = str(technical.get("momentum", "unknown"))
        key_levels = technical.get("key_levels", {"support": [], "resistance": []})
        entry_quality = str(technical.get("entry_quality", "unknown"))
        risk_management_note = str(
            technical.get("risk_management_note", "No technical risk note available.")
        )
        summary = self._summary(ticker, trend, momentum, entry_quality)
        evidence_ids = self._evidence_ids(prior_outputs)
        confidence = "medium" if technical else "low"

        return AgentEnvelope(
            agent_name="technical_analysis",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[
                f"Trend: {trend}",
                f"Momentum: {momentum}",
                f"Entry quality: {entry_quality}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[] if technical else ["No technical metadata available."],
            payload={
                "agent_name": "technical_analysis",
                "ticker": ticker,
                "summary": summary,
                "trend": trend,
                "momentum": momentum,
                "key_levels": key_levels,
                "entry_quality": entry_quality,
                "risk_management_note": risk_management_note,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "open_questions": [] if technical else ["No technical metadata available."],
            },
        )

    def _first_object(self, documents: Iterable[SourceDocument], field_name: str, default: dict) -> dict:
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, dict):
                return raw
        return default

    def _summary(self, ticker: str, trend: str, momentum: str, entry_quality: str) -> str:
        return f"{ticker} technicals show {trend} trend, {momentum} momentum, and {entry_quality} entry quality."

    def _evidence_ids(self, prior_outputs: dict[str, AgentEnvelope]) -> list[str]:
        source = prior_outputs.get("source_verification")
        return list(source.evidence_ids[:5]) if source is not None else []
