"""Minimal orchestration scaffold for the investigation workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .connectors import ConnectorBundle
from .models import AgentEnvelope, ResearchRequest, SourcePacket
from .prompts import INVESTIGATION_AGENT_ORDER
from .run_store import LocalRunStore
from .validation import SchemaValidator


@dataclass(slots=True)
class InvestigationRun:
    request: ResearchRequest
    steps: list[str] = field(default_factory=list)
    outputs: dict[str, AgentEnvelope] = field(default_factory=dict)
    source_packets: dict[str, SourcePacket] = field(default_factory=dict)
    artifact_dir: Path | None = None


class InvestigationOrchestrator:
    """Coordinates the investigation pipeline with runtime validation hooks."""

    def __init__(
        self,
        validator: SchemaValidator | None = None,
        connectors: ConnectorBundle | None = None,
        run_store: LocalRunStore | None = None,
    ) -> None:
        self.validator = validator or SchemaValidator()
        self.connectors = connectors
        self.run_store = run_store

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
        if self.run_store is not None:
            run.artifact_dir = self.run_store.start_run(request, run.steps)
        if self.connectors is not None:
            run.source_packets = {
                ticker: self.connectors.build_source_packet(ticker) for ticker in request.tickers
            }
            if self.run_store is not None and run.artifact_dir is not None:
                self.run_store.record_source_packets(run.artifact_dir, run.source_packets)
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
            if self.run_store is not None and run.artifact_dir is not None:
                self.run_store.record_agent_output(run.artifact_dir, output)
        if self.run_store is not None and run.artifact_dir is not None:
            self.run_store.finish_run(
                run.artifact_dir,
                request=request,
                outputs=run.outputs,
                source_packets=run.source_packets,
                steps=run.steps,
            )
        return run
