from stock_researcher.conversation import ConversationalInterface
from stock_researcher.models import AgentEnvelope, ResearchRequest


def test_conversational_interface_answers_from_prior_research_when_not_time_sensitive() -> None:
    interface = ConversationalInterface()
    request = ResearchRequest(
        request_id="req_conv_001",
        user_query="Why was this rated watch?",
        mode="conversation",
        tickers=["ASML"],
    )
    prior_research = {
        "source_verification": AgentEnvelope(
            agent_name="source_verification",
            ticker="ASML",
            analysis_mode="investigation",
            summary="sources collected",
            confidence="high",
            evidence_ids=["ev_001"],
            payload={
                "agent_name": "source_verification",
                "summary": "sources collected",
                "tickers": ["ASML"],
                "sources_used": [],
                "evidence_ids": ["ev_001"],
                "freshness_status": "fresh",
                "missing_data": [],
                "conflicts_found": [],
                "confidence": "high",
            },
        ),
        "decision_portfolio_fit": AgentEnvelope(
            agent_name="decision_portfolio_fit",
            ticker="ASML",
            analysis_mode="investigation",
            summary="Strong business, but valuation supports Watch.",
            confidence="medium",
            evidence_ids=["ev_010"],
            payload={
                "agent_name": "decision_portfolio_fit",
                "ticker": "ASML",
                "summary": "Strong business, but valuation supports Watch.",
                "decision": "watch",
                "confidence": "medium",
                "best_fit": "long_term_hold",
                "portfolio_flags": [],
                "key_reasons": ["Valuation"],
                "invalidation_triggers": [],
                "evidence_ids": ["ev_010"],
                "open_questions": [],
            },
        ),
    }

    result = interface.respond(request, prior_research=prior_research)

    assert "WATCH" in result.answer
    assert result.envelope.payload["needs_fresh_data"] is False
    assert result.envelope.payload["response_type"] == "direct_answer"


def test_conversational_interface_requests_refresh_for_time_sensitive_question() -> None:
    interface = ConversationalInterface()
    request = ResearchRequest(
        request_id="req_conv_002",
        user_query="Is ASML still worth buying today?",
        mode="conversation",
        tickers=["ASML"],
    )

    result = interface.respond(request, prior_research={})

    assert result.envelope.payload["needs_fresh_data"] is True
    assert result.envelope.payload["recommended_next_action"] == "run_investigation_refresh"
