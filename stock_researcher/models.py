"""Shared typed objects used across agents and orchestrators."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

AnalysisMode = Literal["discovery", "investigation", "comparison", "conversation"]
Confidence = Literal["low", "medium", "high"]
Decision = Literal["buy", "watch", "pass"]


@dataclass(slots=True)
class ResearchRequest:
    request_id: str
    user_query: str
    mode: AnalysisMode
    tickers: list[str] = field(default_factory=list)
    time_horizon: str | None = None
    objective: str | None = None
    risk_tolerance: str | None = None
    portfolio_context_available: bool = False
    requested_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Evidence:
    evidence_id: str
    ticker: str
    claim: str
    as_of_date: str
    source_name: str
    source_type: str
    source_url: str
    published_at: str
    retrieved_at: str
    claim_scope: str
    confidence: Confidence
    value: float | int | str | None = None
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceDocument:
    source_name: str
    source_type: str
    source_url: str
    published_at: str
    retrieved_at: str
    ticker: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourcePacket:
    ticker: str
    filings: list[SourceDocument] = field(default_factory=list)
    market_data: list[SourceDocument] = field(default_factory=list)
    news: list[SourceDocument] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "filings": [item.to_dict() for item in self.filings],
            "market_data": [item.to_dict() for item in self.market_data],
            "news": [item.to_dict() for item in self.news],
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(slots=True)
class AgentEnvelope:
    agent_name: str
    summary: str
    confidence: Confidence
    generated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    ticker: str | None = None
    analysis_mode: AnalysisMode | None = None
    key_points: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    sources_used: list[dict[str, Any]] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecisionPayload:
    ticker: str
    decision: Decision
    confidence: Confidence
    thesis: str
    generated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    time_horizon: str | None = None
    best_fit: str | None = None
    key_reasons_for_decision: list[str] = field(default_factory=list)
    invalidation_triggers: list[str] = field(default_factory=list)
    follow_up_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
