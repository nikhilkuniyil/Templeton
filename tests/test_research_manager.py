from stock_researcher.llm import LLMResponse
from stock_researcher.models import AgentEnvelope, ResearchRequest
from stock_researcher.research_manager import LLMResearchManager


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls.append((system_prompt, user_prompt))
        return LLMResponse(text="LLM final answer", model="fake-model", provider="fake")


def test_research_manager_builds_investigation_prompt() -> None:
    client = FakeLLMClient()
    manager = LLMResearchManager(client)
    request = ResearchRequest(
        request_id="req_001",
        user_query="Is ASML worth buying?",
        mode="investigation",
        tickers=["ASML"],
    )
    outputs = {
        "decision_portfolio_fit": AgentEnvelope(
            agent_name="decision_portfolio_fit",
            ticker="ASML",
            analysis_mode="investigation",
            summary="ASML is currently rated WATCH.",
            confidence="medium",
            evidence_ids=["ev_1"],
            payload={"decision": "watch", "confidence": "medium", "key_reasons": ["Valuation elevated."]},
        )
    }

    answer = manager.compose_investigation_answer(request, outputs)

    assert answer == "LLM final answer"
    assert "Structured research context" in client.calls[0][1]
    assert "ASML is currently rated WATCH." in client.calls[0][1]


def test_research_manager_builds_chat_prompt() -> None:
    client = FakeLLMClient()
    manager = LLMResearchManager(client)
    request = ResearchRequest(
        request_id="req_002",
        user_query="Why is this still watch?",
        mode="conversation",
        tickers=["ASML"],
    )
    prior = {
        "synthesizer": AgentEnvelope(
            agent_name="synthesizer",
            ticker="ASML",
            analysis_mode="investigation",
            summary="ASML memo complete.",
            confidence="medium",
            evidence_ids=["ev_1"],
            payload={"decision": "watch", "confidence": "medium", "memo_sections": {"thesis": "Watch."}},
        )
    }

    answer = manager.answer_chat(request, prior)

    assert answer == "LLM final answer"
    assert "Prior research context" in client.calls[0][1]
