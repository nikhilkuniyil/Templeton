"""Concrete valuation agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class ValuationAgent:
    """Builds a simple valuation view from source metadata."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        docs = [*packet.market_data, *packet.filings, *packet.news]
        current_valuation = self._first_object(docs, "current_valuation", {})
        scenario_ranges = self._first_object(docs, "scenario_ranges", {})
        market_implied_expectations = self._first_list(docs, "market_implied_expectations")
        valuation_label = self._infer_label(current_valuation)
        methods_used = self._first_list(docs, "valuation_methods") or ["metadata_proxy"]
        evidence_ids = self._evidence_ids(prior_outputs)
        summary = self._summary(ticker, valuation_label, current_valuation)
        confidence = "medium" if current_valuation else "low"

        return AgentEnvelope(
            agent_name="valuation",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[
                f"Valuation label: {valuation_label}",
                f"Methods used: {', '.join(methods_used)}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[] if current_valuation else ["No valuation metadata available yet."],
            payload={
                "agent_name": "valuation",
                "ticker": ticker,
                "summary": summary,
                "methods_used": methods_used,
                "current_valuation": current_valuation,
                "scenario_ranges": scenario_ranges,
                "market_implied_expectations": market_implied_expectations,
                "valuation_label": valuation_label,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "open_questions": [] if current_valuation else ["No valuation metadata available yet."],
            },
        )

    def _first_object(self, documents: Iterable[SourceDocument], field_name: str, default: dict) -> dict:
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, dict):
                return raw
        return default

    def _first_list(self, documents: Iterable[SourceDocument], field_name: str) -> list[str]:
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, list):
                return [str(item) for item in raw]
        return []

    def _infer_label(self, current_valuation: dict) -> str:
        pe = current_valuation.get("pe")
        if isinstance(pe, (int, float)):
            if pe >= 35:
                return "expensive"
            if pe >= 25:
                return "fair_to_expensive"
            if pe >= 15:
                return "fair"
            return "cheap"
        return "unknown"

    def _summary(self, ticker: str, valuation_label: str, current_valuation: dict) -> str:
        pe = current_valuation.get("pe", "n/a")
        return f"{ticker} screens as {valuation_label} on current metadata, with P/E around {pe}."

    def _evidence_ids(self, prior_outputs: dict[str, AgentEnvelope]) -> list[str]:
        source = prior_outputs.get("source_verification")
        return list(source.evidence_ids[:5]) if source is not None else []
