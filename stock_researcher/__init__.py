"""Core package for the stock research system scaffold."""

from .models import (
    AgentEnvelope,
    DecisionPayload,
    Evidence,
    ResearchRequest,
    SourceDocument,
    SourcePacket,
)
from .conversation import ConversationalInterface

__all__ = [
    "AgentEnvelope",
    "ConversationalInterface",
    "DecisionPayload",
    "Evidence",
    "ResearchRequest",
    "SourceDocument",
    "SourcePacket",
]
