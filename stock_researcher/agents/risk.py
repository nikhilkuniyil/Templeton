"""Concrete risk agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class RiskAgent:
    """Builds a basic bear case from metadata and prior outputs."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        docs = [*packet.filings, *packet.news, *packet.market_data]
        risk_items = self._collect_objects(docs, "core_risks")
        if not risk_items:
            risk_items = self._fallback_risks(prior_outputs)
        thesis_breakers = self._collect_strings(docs, "thesis_breakers")
        monitoring_indicators = self._collect_strings(docs, "monitoring_indicators")
        evidence_ids = self._evidence_ids(prior_outputs)
        summary = self._summary(ticker, risk_items)
        confidence = "medium" if docs else "low"

        return AgentEnvelope(
            agent_name="risk",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[f"Core risks identified: {len(risk_items)}"],
            evidence_ids=evidence_ids,
            open_questions=[] if docs else ["No risk metadata available."],
            payload={
                "agent_name": "risk",
                "ticker": ticker,
                "summary": summary,
                "core_risks": risk_items,
                "thesis_breakers": thesis_breakers,
                "monitoring_indicators": monitoring_indicators,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "open_questions": [] if docs else ["No risk metadata available."],
            },
        )

    def _collect_objects(self, documents: Iterable[SourceDocument], field_name: str) -> list[dict]:
        results: list[dict] = []
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        results.append(item)
        return results

    def _collect_strings(self, documents: Iterable[SourceDocument], field_name: str) -> list[str]:
        values: list[str] = []
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
        return list(dict.fromkeys(values))

    def _fallback_risks(self, prior_outputs: dict[str, AgentEnvelope]) -> list[dict]:
        business = prior_outputs.get("business_quality")
        if business is None:
            return []
        vulnerabilities = business.payload.get("vulnerabilities", [])
        results = []
        for item in vulnerabilities:
            results.append({"risk": item, "severity": "medium", "likelihood": "medium"})
        return results

    def _summary(self, ticker: str, risk_items: list[dict]) -> str:
        if not risk_items:
            return f"{ticker} risk picture is not fully characterized yet."
        top = risk_items[0]
        return f"Top current risk for {ticker}: {top.get('risk', 'unknown risk')}."

    def _evidence_ids(self, prior_outputs: dict[str, AgentEnvelope]) -> list[str]:
        source = prior_outputs.get("source_verification")
        return list(source.evidence_ids[:5]) if source is not None else []
