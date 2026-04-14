"""Simple runtime for implemented agents and placeholder responses."""

from __future__ import annotations

from typing import Any

from ..models import AgentEnvelope, ResearchRequest, SourcePacket
from .business_quality import BusinessQualityAgent
from .router_planner import RouterPlannerAgent
from .source_verification import SourceVerificationAgent


class AgentRuntime:
    """Dispatches implemented agents and falls back to placeholder envelopes."""

    def __init__(self) -> None:
        self.business_quality = BusinessQualityAgent()
        self.router_planner = RouterPlannerAgent()
        self.source_verification = SourceVerificationAgent()

    def execute(
        self,
        agent_name: str,
        request: ResearchRequest,
        prior_outputs: dict[str, AgentEnvelope],
        source_packets: dict[str, SourcePacket],
    ) -> AgentEnvelope:
        if agent_name == "router_planner":
            return self.router_planner.run(request)
        if agent_name == "source_verification":
            return self.source_verification.run(request=request, source_packets=source_packets)
        if agent_name == "business_quality":
            return self.business_quality.run(
                request=request,
                source_packets=source_packets,
                prior_outputs=prior_outputs,
            )
        return self._placeholder(agent_name=agent_name, request=request, prior_outputs=prior_outputs)

    def _placeholder(
        self,
        agent_name: str,
        request: ResearchRequest,
        prior_outputs: dict[str, AgentEnvelope],
    ) -> AgentEnvelope:
        ticker = request.tickers[0] if request.tickers else None
        summary = f"{agent_name} is not implemented yet."
        payload: dict[str, Any]

        if agent_name == "business_quality":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "business_model": "Pending implementation.",
                "revenue_drivers": [],
                "competitive_advantages": [],
                "vulnerabilities": [],
                "durability_rating": "medium",
                "evidence_ids": [],
                "confidence": "low",
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "financial_quality":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "growth_profile": {},
                "margin_profile": {},
                "cash_flow_profile": {},
                "balance_sheet_profile": {},
                "capital_allocation": {},
                "overall_quality_rating": "medium",
                "evidence_ids": [],
                "confidence": "low",
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "valuation":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "methods_used": [],
                "current_valuation": {},
                "scenario_ranges": {},
                "market_implied_expectations": [],
                "valuation_label": "unknown",
                "evidence_ids": [],
                "confidence": "low",
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "news_catalyst":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "positive_catalysts": [],
                "negative_catalysts": [],
                "recent_events": [],
                "evidence_ids": [],
                "confidence": "low",
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "risk":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "core_risks": [],
                "thesis_breakers": [],
                "monitoring_indicators": [],
                "evidence_ids": [],
                "confidence": "low",
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "decision_portfolio_fit":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "decision": "watch",
                "confidence": "low",
                "best_fit": "unknown",
                "portfolio_flags": [],
                "key_reasons": ["Agent not implemented yet."],
                "invalidation_triggers": [],
                "evidence_ids": [],
                "open_questions": ["Agent not implemented yet."],
            }
        elif agent_name == "synthesizer":
            payload = {
                "agent_name": agent_name,
                "ticker": ticker,
                "summary": summary,
                "decision": "watch",
                "confidence": "low",
                "memo_sections": {
                    "status": "Synthesis pending full agent implementation.",
                    "prior_outputs_seen": str(len(prior_outputs)),
                },
                "evidence_ids": [],
                "open_questions": ["Agent not implemented yet."],
            }
        else:
            raise ValueError(f"Unknown agent {agent_name!r}")

        return AgentEnvelope(
            agent_name=agent_name,
            ticker=ticker,
            analysis_mode=request.mode,
            summary=summary,
            confidence="low",
            key_points=["Placeholder output used."],
            open_questions=["Agent not implemented yet."],
            payload=payload,
        )
