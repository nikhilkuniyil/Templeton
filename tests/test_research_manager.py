from stock_researcher.llm import (
    AnthropicMessagesClient,
    GeminiGenerateContentClient,
    LLMResponse,
    OpenAIResponsesClient,
)
from stock_researcher.models import AgentEnvelope, ResearchRequest
from stock_researcher.research_manager import LLMResearchManager, ManagerLoop


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


def test_openai_client_extracts_output_text() -> None:
    client = OpenAIResponsesClient(
        api_key="test-key",
        post_json=lambda url, headers, payload: {"output_text": "OpenAI answer"},
    )
    response = client.generate("system", "user")
    assert response.text == "OpenAI answer"
    assert response.provider == "openai"


def test_anthropic_client_extracts_text_blocks() -> None:
    client = AnthropicMessagesClient(
        api_key="test-key",
        post_json=lambda url, headers, payload: {
            "content": [{"type": "text", "text": "Claude answer"}]
        },
    )
    response = client.generate("system", "user")
    assert response.text == "Claude answer"
    assert response.provider == "anthropic"


def test_gemini_client_extracts_candidate_text() -> None:
    client = GeminiGenerateContentClient(
        api_key="test-key",
        post_json=lambda url, headers, payload: {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini answer"}]
                    }
                }
            ]
        },
    )
    response = client.generate("system", "user")
    assert response.text == "Gemini answer"
    assert response.provider == "gemini"


def test_manager_loop_always_includes_verifier_and_returns_outputs() -> None:
    client = FakeLLMClient()
    loop = ManagerLoop(client)
    request = ResearchRequest(
        request_id="req_003",
        user_query="Is ASML worth buying?",
        mode="investigation",
        tickers=["ASML"],
    )

    call_order: list[str] = []

    def executor(agent_name, request, prior_outputs, source_packets):
        call_order.append(agent_name)
        if agent_name == "synthesizer":
            payload = {
                "agent_name": "synthesizer",
                "ticker": "ASML",
                "summary": "ASML memo complete.",
                "decision": "watch",
                "confidence": "medium",
                "memo_sections": {"thesis": "Watch.", "verification": "Passed."},
                "evidence_map": {"verification": ["ev_2"]},
                "evidence_ids": ["ev_1", "ev_2"],
                "open_questions": [],
            }
        elif agent_name == "verifier":
            payload = {
                "agent_name": "verifier",
                "ticker": "ASML",
                "summary": "ASML verification passed.",
                "verifier_status": "pass",
                "adjusted_confidence": "medium",
                "stale_data": False,
                "contradictions": [],
                "unsupported_claims": [],
                "missing_evidence": [],
                "warnings": [],
                "recommended_action": "accept",
                "evidence_ids": ["ev_2"],
                "open_questions": [],
            }
        elif agent_name == "decision_portfolio_fit":
            payload = {
                "agent_name": "decision_portfolio_fit",
                "ticker": "ASML",
                "summary": "ASML is currently rated WATCH.",
                "decision": "watch",
                "confidence": "medium",
                "best_fit": "long_term_hold",
                "portfolio_flags": [],
                "key_reasons": ["Valuation elevated."],
                "invalidation_triggers": [],
                "evidence_ids": ["ev_1"],
                "open_questions": [],
            }
        elif agent_name == "source_verification":
            payload = {
                "agent_name": "source_verification",
                "summary": "sources collected",
                "tickers": ["ASML"],
                "sources_used": [],
                "evidence_ids": ["ev_1"],
                "freshness_status": "fresh",
                "missing_data": [],
                "conflicts_found": [],
                "confidence": "medium",
            }
        elif agent_name == "router_planner":
            payload = {
                "agent_name": "router_planner",
                "summary": "plan ready",
                "mode": "investigation",
                "tickers": ["ASML"],
                "time_horizon": "long_term",
                "objective": "long_term_compounding",
                "tasks": ["source_verification", "decision_portfolio_fit", "verifier", "synthesizer"],
                "needs_fresh_data": True,
                "clarifying_question": None,
                "confidence": "medium",
            }
        else:
            payload = {
                "agent_name": agent_name,
                "ticker": "ASML",
                "summary": f"{agent_name} summary",
                "confidence": "medium",
                "evidence_ids": [],
                "open_questions": [],
            }
        return AgentEnvelope(
            agent_name=agent_name,
            ticker="ASML",
            analysis_mode="investigation",
            summary=f"{agent_name} completed",
            confidence="medium",
            evidence_ids=payload.get("evidence_ids", []),
            payload=payload,
        )

    result = loop.run(request, executor, source_packets={})

    assert "verifier" in result.agents_run
    assert "verifier" in result.outputs
    assert result.outputs["verifier"].payload["verifier_status"] == "pass"
