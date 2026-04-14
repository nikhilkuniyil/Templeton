"""Concrete news / catalyst agent implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AgentEnvelope, ResearchRequest, SourceDocument, SourcePacket


class NewsCatalystAgent:
    """Summarizes recent catalysts from source metadata."""

    def run(
        self,
        request: ResearchRequest,
        source_packets: dict[str, SourcePacket],
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0]
        packet = source_packets.get(ticker, SourcePacket(ticker=ticker))
        docs = [*packet.news, *packet.filings]
        positive_catalysts = self._collect(docs, "positive_catalysts")
        negative_catalysts = self._collect(docs, "negative_catalysts")
        recent_events = self._events(packet.news)
        evidence_ids = self._evidence_ids(prior_outputs)
        summary = self._summary(ticker, positive_catalysts, negative_catalysts)
        confidence = "medium" if docs else "low"

        return AgentEnvelope(
            agent_name="news_catalyst",
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence=confidence,
            key_points=[
                f"Positive catalysts: {len(positive_catalysts)}",
                f"Negative catalysts: {len(negative_catalysts)}",
            ],
            evidence_ids=evidence_ids,
            open_questions=[] if docs else ["No news or catalyst metadata available."],
            payload={
                "agent_name": "news_catalyst",
                "ticker": ticker,
                "summary": summary,
                "positive_catalysts": positive_catalysts,
                "negative_catalysts": negative_catalysts,
                "recent_events": recent_events,
                "evidence_ids": evidence_ids,
                "confidence": confidence,
                "open_questions": [] if docs else ["No news or catalyst metadata available."],
            },
        )

    def _collect(self, documents: Iterable[SourceDocument], field_name: str) -> list[str]:
        values: list[str] = []
        for document in documents:
            raw = document.metadata.get(field_name)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
        return list(dict.fromkeys(values))

    def _events(self, news_docs: list[SourceDocument]) -> list[dict]:
        events: list[dict] = []
        for document in news_docs:
            events.append(
                {
                    "event_date": document.published_at[:10],
                    "event_type": document.metadata.get("event_type", "news"),
                    "headline": document.source_name,
                    "expected_impact": document.metadata.get("expected_impact", "medium"),
                }
            )
        return events

    def _summary(self, ticker: str, positive_catalysts: list[str], negative_catalysts: list[str]) -> str:
        positive = ", ".join(positive_catalysts[:2]) if positive_catalysts else "limited positive catalysts"
        negative = ", ".join(negative_catalysts[:2]) if negative_catalysts else "limited negative catalysts"
        return f"{ticker} catalyst picture: positives include {positive}; main overhangs include {negative}."

    def _evidence_ids(self, prior_outputs: dict[str, AgentEnvelope]) -> list[str]:
        source = prior_outputs.get("source_verification")
        return list(source.evidence_ids[:5]) if source is not None else []
