from stock_researcher.connectors import (
    ConnectorBundle,
    StaticFilingsClient,
    StaticMarketDataClient,
    StaticNewsClient,
)
from stock_researcher.agents import AgentRuntime
from stock_researcher.demo_data import demo_connector_bundle
from stock_researcher.models import AgentEnvelope, ResearchRequest, SourceDocument
from stock_researcher.orchestrator import InvestigationOrchestrator
from stock_researcher.validation import ValidationError


def test_investigation_orchestrator_builds_expected_plan() -> None:
    request = ResearchRequest(
        request_id="req_001",
        user_query="Is ASML worth buying?",
        mode="investigation",
        tickers=["ASML"],
    )

    run = InvestigationOrchestrator().run(request)

    assert run.steps[0] == "router_planner"
    assert run.steps[-1] == "synthesizer"
    assert run.outputs == {}


def test_investigation_orchestrator_collects_agent_outputs() -> None:
    request = ResearchRequest(
        request_id="req_002",
        user_query="Is ASML worth buying?",
        mode="investigation",
        tickers=["ASML"],
    )

    def executor(
        agent_name: str,
        request: ResearchRequest,
        prior_outputs: dict[str, AgentEnvelope],
        source_packets: dict[str, object],
    ) -> AgentEnvelope:
        return AgentEnvelope(
            agent_name=agent_name,
            ticker=request.tickers[0],
            analysis_mode=request.mode,
            summary=f"{agent_name} completed",
            confidence="medium",
            key_points=[f"Prior outputs: {len(prior_outputs)}"],
            payload=_payload_for(agent_name, request.tickers[0]),
        )

    run = InvestigationOrchestrator().run(request, agent_executor=executor)

    assert len(run.outputs) == len(run.steps)
    assert run.outputs["synthesizer"].summary == "synthesizer completed"


def test_investigation_orchestrator_builds_source_packets_from_connectors() -> None:
    request = ResearchRequest(
        request_id="req_003",
        user_query="Investigate ASML",
        mode="investigation",
        tickers=["ASML"],
    )
    connectors = ConnectorBundle(
        filings=StaticFilingsClient(
            {"ASML": [_source_doc("ASML annual report", "company_filing_or_release", "ASML")]}
        ),
        market_data=StaticMarketDataClient(
            {"ASML": [_source_doc("ASML price history", "market_data", "ASML")]}
        ),
        news=StaticNewsClient({"ASML": [_source_doc("ASML news item", "news", "ASML")]}),
    )

    run = InvestigationOrchestrator(connectors=connectors).run(request)

    packet = run.source_packets["ASML"]
    assert len(packet.filings) == 1
    assert len(packet.market_data) == 1
    assert len(packet.news) == 1


def test_investigation_orchestrator_rejects_invalid_payloads() -> None:
    request = ResearchRequest(
        request_id="req_004",
        user_query="Investigate ASML",
        mode="investigation",
        tickers=["ASML"],
    )

    def executor(
        agent_name: str,
        request: ResearchRequest,
        prior_outputs: dict[str, AgentEnvelope],
        source_packets: dict[str, object],
    ) -> AgentEnvelope:
        return AgentEnvelope(
            agent_name=agent_name,
            ticker=request.tickers[0],
            analysis_mode=request.mode,
            summary="invalid payload",
            confidence="medium",
            payload={"summary": "missing required fields"},
        )

    try:
        InvestigationOrchestrator().run(request, agent_executor=executor)
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for invalid payload")


def test_agent_runtime_executes_real_source_verification_agent() -> None:
    request = ResearchRequest(
        request_id="req_005",
        user_query="Investigate ASML",
        mode="investigation",
        tickers=["ASML"],
    )
    connectors = demo_connector_bundle()
    runtime = AgentRuntime()

    run = InvestigationOrchestrator(connectors=connectors).run(request, agent_executor=runtime.execute)

    source_output = run.outputs["source_verification"]
    assert source_output.payload["freshness_status"] == "fresh"
    assert len(source_output.payload["sources_used"]) == 3
    assert run.outputs["router_planner"].payload["mode"] == "investigation"
    assert run.outputs["decision_portfolio_fit"].payload["decision"] == "watch"
    assert run.outputs["synthesizer"].payload["decision"] == "watch"
    assert "valuation leaves less room for error" in " ".join(
        run.outputs["decision_portfolio_fit"].payload["key_reasons"]
    ).lower()


def _source_doc(name: str, source_type: str, ticker: str) -> SourceDocument:
    return SourceDocument(
        source_name=name,
        source_type=source_type,
        source_url="https://example.com",
        published_at="2026-04-10T00:00:00Z",
        retrieved_at="2026-04-14T09:00:00-07:00",
        ticker=ticker,
    )


def _payload_for(agent_name: str, ticker: str) -> dict[str, object]:
    shared = {
        "ticker": ticker,
        "summary": f"{agent_name} summary",
        "confidence": "medium",
    }
    if agent_name == "router_planner":
        return {
            "agent_name": agent_name,
            "summary": "plan ready",
            "mode": "investigation",
            "tickers": [ticker],
            "time_horizon": "long_term",
            "objective": "long_term_compounding",
            "tasks": ["fetch_sources", "make_decision"],
            "needs_fresh_data": True,
            "clarifying_question": None,
            "confidence": "medium",
        }
    if agent_name == "source_verification":
        return {
            "agent_name": agent_name,
            "summary": "sources collected",
            "tickers": [ticker],
            "sources_used": [
                {
                    "source_name": "ASML annual report",
                    "source_type": "company_filing_or_release",
                    "published_at": "2026-01-28T00:00:00Z",
                    "retrieved_at": "2026-04-14T09:00:00-07:00",
                }
            ],
            "evidence_ids": ["ev_001"],
            "freshness_status": "fresh",
            "missing_data": [],
            "conflicts_found": [],
            "confidence": "medium",
        }
    if agent_name == "business_quality":
        return {
            "agent_name": agent_name,
            **shared,
            "business_model": "Sells lithography systems and services.",
            "revenue_drivers": ["EUV systems"],
            "competitive_advantages": ["Technology leadership"],
            "vulnerabilities": ["Capex cyclicality"],
            "durability_rating": "high",
            "evidence_ids": ["ev_010"],
            "open_questions": [],
        }
    if agent_name == "financial_quality":
        return {
            "agent_name": agent_name,
            **shared,
            "growth_profile": {"revenue_growth_trend": "positive"},
            "margin_profile": {"gross_margin_trend": "stable"},
            "cash_flow_profile": {"free_cash_flow_quality": "strong"},
            "balance_sheet_profile": {"debt_risk": "low"},
            "capital_allocation": {"dilution_risk": "low"},
            "overall_quality_rating": "high",
            "evidence_ids": ["ev_020"],
            "open_questions": [],
        }
    if agent_name == "valuation":
        return {
            "agent_name": agent_name,
            **shared,
            "methods_used": ["historical_multiples"],
            "current_valuation": {"pe": 32.0},
            "scenario_ranges": {"base": {"fair_value": 900}},
            "market_implied_expectations": ["High growth"],
            "valuation_label": "fair_to_expensive",
            "evidence_ids": ["ev_030"],
            "open_questions": [],
        }
    if agent_name == "news_catalyst":
        return {
            "agent_name": agent_name,
            **shared,
            "positive_catalysts": ["Strong AI demand"],
            "negative_catalysts": ["Export restrictions"],
            "recent_events": [{"event_date": "2026-04-10", "event_type": "news"}],
            "evidence_ids": ["ev_040"],
            "open_questions": [],
        }
    if agent_name == "technical_analysis":
        return {
            "agent_name": agent_name,
            **shared,
            "trend": "uptrend",
            "momentum": "positive",
            "key_levels": {"support": [850], "resistance": [950]},
            "entry_quality": "neutral",
            "risk_management_note": "Watch support on pullbacks.",
            "evidence_ids": ["ev_035"],
            "open_questions": [],
        }
    if agent_name == "risk":
        return {
            "agent_name": agent_name,
            **shared,
            "core_risks": [{"risk": "Capex slowdown", "severity": "high", "likelihood": "medium"}],
            "thesis_breakers": ["Demand deterioration"],
            "monitoring_indicators": ["Order growth"],
            "evidence_ids": ["ev_050"],
            "open_questions": [],
        }
    if agent_name == "decision_portfolio_fit":
        return {
            "agent_name": agent_name,
            **shared,
            "decision": "watch",
            "best_fit": "long_term_hold",
            "portfolio_flags": ["Check semiconductor exposure"],
            "key_reasons": ["High quality", "Valuation not cheap"],
            "invalidation_triggers": ["Order weakness"],
            "evidence_ids": ["ev_020", "ev_030"],
            "open_questions": [],
        }
    if agent_name == "synthesizer":
        return {
            "agent_name": agent_name,
            **shared,
            "decision": "watch",
            "memo_sections": {"thesis": "Strong business, watch valuation."},
            "evidence_ids": ["ev_010", "ev_020", "ev_030"],
            "open_questions": [],
        }
    raise AssertionError(f"Unhandled agent {agent_name}")
