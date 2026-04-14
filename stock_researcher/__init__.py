"""Core package for the stock research system scaffold."""

from .models import (
    AgentEnvelope,
    DecisionPayload,
    Evidence,
    ResearchRequest,
    SourceDocument,
    SourcePacket,
)

__all__ = [
    "AgentEnvelope",
    "DecisionPayload",
    "Evidence",
    "ResearchRequest",
    "SourceDocument",
    "SourcePacket",
]
