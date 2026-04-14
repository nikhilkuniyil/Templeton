"""Minimal orchestration scaffold for the investigation workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .connectors import ConnectorBundle
from .models import AgentEnvelope, ResearchRequest, SourcePacket
from .prompts import INVESTIGATION_AGENT_ORDER
from .validation import SchemaValidator


@dataclass(slots=True)
class InvestigationRun:
    request: ResearchRequest
    steps: list[str] = field(default_factory=list)
    outputs: dict[str, AgentEnvelope] = field(default_factory=dict)
    source_packets: dict[str, SourcePacket] = field(default_factory=dict)


class InvestigationOrchestrator:
    """Coordinates the investigation pipeline with runtime validation hooks."""

    def __init__(
        self,
        validator: SchemaValidator | None = None,
        connectors: ConnectorBundle | None = None,
    ) -> None:
        self.validator = validator or SchemaValidator()
        self.connectors = connectors

    def build_plan(self, request: ResearchRequest) -> list[str]:
        self.validator.validate("research_request", request)
        if request.mode != "investigation":
            raise ValueError(f"Unsupported mode for this orchestrator: {request.mode}")
        if not request.tickers:
            raise ValueError("Investigation mode requires at least one ticker")
        return list(INVESTIGATION_AGENT_ORDER)

    def run(
        self,
        request: ResearchRequest,
        agent_executor: Any | None = None,
    ) -> InvestigationRun:
        run = InvestigationRun(request=request)
        run.steps = self.build_plan(request)
        if self.connectors is not None:
            run.source_packets = {
                ticker: self.connectors.build_source_packet(ticker) for ticker in request.tickers
            }
        if agent_executor is None:
            return run

        for agent_name in run.steps:
            output = agent_executor(
                agent_name=agent_name,
                request=request,
                prior_outputs=run.outputs,
                source_packets=run.source_packets,
            )
            if not isinstance(output, AgentEnvelope):
                raise TypeError(f"{agent_name} must return AgentEnvelope, got {type(output)!r}")
            self.validator.validate("agent_envelope", output)
            if output.agent_name != agent_name:
                raise ValueError(
                    f"Agent output mismatch: expected {agent_name!r}, got {output.agent_name!r}"
                )
            if output.payload:
                self.validator.validate(agent_name, output.payload)
            run.outputs[agent_name] = output
        return run
