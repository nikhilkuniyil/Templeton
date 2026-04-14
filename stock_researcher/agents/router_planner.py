"""Concrete router / planner implementation."""

from __future__ import annotations

from ..models import AgentEnvelope, ResearchRequest
from ..prompts import INVESTIGATION_AGENT_ORDER


class RouterPlannerAgent:
    """Produces a minimal investigation plan from the request."""

    def run(self, request: ResearchRequest) -> AgentEnvelope:
        summary = f"Plan ready for investigating {', '.join(request.tickers)}."
        return AgentEnvelope(
            agent_name="router_planner",
            ticker=request.tickers[0] if len(request.tickers) == 1 else None,
            analysis_mode=request.mode,
            summary=summary,
            confidence="high",
            key_points=[
                f"Mode: {request.mode}",
                f"Time horizon: {request.time_horizon or 'unspecified'}",
            ],
            payload={
                "agent_name": "router_planner",
                "summary": summary,
                "mode": request.mode,
                "tickers": request.tickers,
                "time_horizon": request.time_horizon,
                "objective": request.objective,
                "tasks": list(INVESTIGATION_AGENT_ORDER[1:]),
                "needs_fresh_data": True,
                "clarifying_question": None,
                "confidence": "high",
            },
        )
