"""Command-line interface for the stock research scaffold."""

from __future__ import annotations

import argparse
import json
import os
from uuid import uuid4

from .agents import AgentRuntime
from .connectors import (
    ConnectorBundle,
    ConnectorError,
    FinancialDatasetsFilingsClient,
    FinancialDatasetsMarketDataClient,
    SecCompanyFactsMarketDataClient,
    SecFilingsClient,
    YahooFinanceNewsClient,
)
from .conversation import ConversationalInterface
from .benchmarks import BenchmarkHarness, format_suite_result
from .demo_data import demo_connector_bundle
from .llm import LLMError, OpenAIResponsesClient
from .models import AgentEnvelope, ResearchRequest
from .orchestrator import InvestigationOrchestrator
from .research_manager import LLMResearchManager
from .run_store import LocalRunStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="templeton", description="CLI for the stock research system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    investigate = subparsers.add_parser("investigate", help="Run the investigation workflow for a ticker")
    investigate.add_argument("ticker", help="Ticker symbol to investigate")
    investigate.add_argument("--query", default=None, help="Optional research question")
    investigate.add_argument("--time-horizon", default="long_term", help="Investment horizon label")
    investigate.add_argument("--objective", default="long_term_compounding", help="Research objective")
    investigate.add_argument("--json", action="store_true", help="Print raw JSON output")
    investigate.add_argument("--llm", action="store_true", help="Use an LLM to produce an upgraded final memo")
    investigate.add_argument("--llm-model", default="gpt-5.4-mini", help="LLM model to use when --llm is enabled")
    investigate.add_argument("--demo", action="store_true", help="Use built-in demo connector data")
    investigate.add_argument("--live-filings", action="store_true", help="Use live SEC filings with empty market/news connectors")
    investigate.add_argument(
        "--financial-datasets",
        action="store_true",
        help="Use Financial Datasets for market data while keeping SEC filings and Yahoo news",
    )
    investigate.add_argument(
        "--store-dir",
        default=".templeton",
        help="Local directory for run artifacts and history",
    )
    investigate.add_argument(
        "--sec-user-agent",
        default="TempletonResearch/0.1 (contact: local@example.com)",
        help="User-Agent header for SEC requests",
    )

    chat = subparsers.add_parser("chat", help="Ask a conversational research question")
    chat.add_argument("ticker", help="Ticker symbol to discuss")
    chat.add_argument("question", help="Question to ask")
    chat.add_argument("--llm", action="store_true", help="Use an LLM for the final conversational answer")
    chat.add_argument("--llm-model", default="gpt-5.4-mini", help="LLM model to use when --llm is enabled")
    chat.add_argument("--demo", action="store_true", help="Use built-in demo connector data")
    chat.add_argument("--refresh", action="store_true", help="Run a fresh investigation before answering")
    chat.add_argument("--live-filings", action="store_true", help="Use live SEC filings with empty market/news connectors")
    chat.add_argument(
        "--financial-datasets",
        action="store_true",
        help="Use Financial Datasets for market data while keeping SEC filings and Yahoo news",
    )
    chat.add_argument(
        "--store-dir",
        default=".templeton",
        help="Local directory for run artifacts and history",
    )
    chat.add_argument(
        "--sec-user-agent",
        default="TempletonResearch/0.1 (contact: local@example.com)",
        help="User-Agent header for SEC requests",
    )

    benchmark = subparsers.add_parser("benchmark", help="Run the local benchmark suite")
    benchmark.add_argument(
        "--suite",
        default=None,
        help="Optional path to a benchmark suite JSON file",
    )
    benchmark.add_argument(
        "--store-dir",
        default=".templeton",
        help="Local directory for benchmark run artifacts",
    )
    benchmark.add_argument("--json", action="store_true", help="Print raw JSON output")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "investigate":
        return _handle_investigate(args)
    if args.command == "chat":
        return _handle_chat(args)
    if args.command == "benchmark":
        return _handle_benchmark(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _handle_investigate(args) -> int:
    try:
        connectors = _connector_bundle_from_args(args)
    except ConnectorError as exc:
        print(f"Connector error: {exc}")
        return 1
    run_store = LocalRunStore(args.store_dir)
    runtime = AgentRuntime(run_store=run_store)
    orchestrator = InvestigationOrchestrator(connectors=connectors, run_store=run_store)
    ticker = args.ticker.upper()
    request = ResearchRequest(
        request_id=f"req_{uuid4().hex[:8]}",
        user_query=args.query or f"Investigate {ticker}",
        mode="investigation",
        tickers=[ticker],
        time_horizon=args.time_horizon,
        objective=args.objective,
    )
    try:
        run = orchestrator.run(request, agent_executor=runtime.execute)
    except ConnectorError as exc:
        print(f"Connector error: {exc}")
        return 1

    if args.json:
        print(json.dumps(_run_to_dict(run.outputs), indent=2))
        return 0

    print(f"Investigation: {ticker}")
    print(f"Question: {request.user_query}")
    if run.artifact_dir is not None:
        print(f"Run artifacts: {run.artifact_dir}")
    for agent_name in run.steps:
        output = run.outputs.get(agent_name)
        if output is None:
            continue
        print(f"\n[{agent_name}]")
        print(output.summary)
        if agent_name == "synthesizer":
            _print_synthesizer_sections(output)
            continue
        if output.key_points:
            for point in output.key_points[:3]:
                print(f"- {point}")
    if args.llm:
        try:
            manager = _llm_manager_from_args(args)
            llm_answer = manager.compose_investigation_answer(request, run.outputs)
        except (ConnectorError, LLMError) as exc:
            print(f"\n[llm]\nLLM error: {exc}")
            return 1
        print("\n[llm]")
        print(llm_answer)
    return 0


def _handle_chat(args) -> int:
    ticker = args.ticker.upper()
    try:
        connectors = _connector_bundle_from_args(args)
    except ConnectorError as exc:
        print(f"Connector error: {exc}")
        return 1
    run_store = LocalRunStore(args.store_dir)
    runtime = AgentRuntime(run_store=run_store)
    orchestrator = InvestigationOrchestrator(connectors=connectors, run_store=run_store)
    request = ResearchRequest(
        request_id=f"req_{uuid4().hex[:8]}",
        user_query=args.question,
        mode="conversation",
        tickers=[ticker],
    )
    prior_research: dict[str, AgentEnvelope] = run_store.load_latest_outputs(ticker)
    if args.refresh:
        refresh_request = ResearchRequest(
            request_id=request.request_id,
            user_query=f"Investigate {ticker}",
            mode="investigation",
            tickers=[ticker],
            time_horizon="long_term",
            objective="long_term_compounding",
        )
        try:
            run = orchestrator.run(refresh_request, agent_executor=runtime.execute)
        except ConnectorError as exc:
            print(f"Connector error: {exc}")
            return 1
        prior_research = run.outputs

    interface = ConversationalInterface()
    if args.llm and prior_research:
        try:
            manager = _llm_manager_from_args(args)
            answer = manager.answer_chat(request, prior_research)
        except (ConnectorError, LLMError) as exc:
            print(f"LLM error: {exc}")
            return 1
        print(answer)
        return 0

    result = interface.respond(request, prior_research=prior_research)
    print(result.answer)

    next_action = result.envelope.payload.get("recommended_next_action")
    if next_action:
        print(f"Next action: {next_action}")
    return 0


def _run_to_dict(outputs: dict[str, AgentEnvelope]) -> dict[str, dict]:
    return {name: envelope.to_dict() for name, envelope in outputs.items()}


def _print_synthesizer_sections(output: AgentEnvelope) -> None:
    sections = output.payload.get("memo_sections", {})
    if not isinstance(sections, dict):
        return
    for label, key in (
        ("Decision", "decision"),
        ("What changed", "what_changed"),
        ("Verification", "verification"),
        ("Bull case", "bull_case"),
        ("Bear case", "bear_case"),
    ):
        value = sections.get(key)
        if isinstance(value, str) and value.strip():
            print(f"- {label}: {value}")


def _handle_benchmark(args) -> int:
    harness = BenchmarkHarness(run_store=LocalRunStore(args.store_dir))
    result = harness.run_suite(args.suite)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print(format_suite_result(result))
    return 0


def _connector_bundle_from_args(args) -> ConnectorBundle | None:
    if getattr(args, "demo", False):
        return demo_connector_bundle()
    if getattr(args, "financial_datasets", False):
        api_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
        if not api_key:
            raise ConnectorError(
                "FINANCIAL_DATASETS_API_KEY is not set. Export it before using --financial-datasets."
            )
        sec_fallback = SecFilingsClient(user_agent=args.sec_user_agent)
        return ConnectorBundle(
            filings=FinancialDatasetsFilingsClient(
                api_key=api_key,
                user_agent=args.sec_user_agent,
                fallback_client=sec_fallback,
            ),
            market_data=FinancialDatasetsMarketDataClient(api_key=api_key),
            news=YahooFinanceNewsClient(user_agent=args.sec_user_agent),
        )
    if getattr(args, "live_filings", False):
        return ConnectorBundle(
            filings=SecFilingsClient(user_agent=args.sec_user_agent),
            market_data=SecCompanyFactsMarketDataClient(user_agent=args.sec_user_agent),
            news=YahooFinanceNewsClient(user_agent=args.sec_user_agent),
        )
    return None


def _llm_manager_from_args(args) -> LLMResearchManager:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConnectorError("OPENAI_API_KEY is not set. Export it before using --llm.")
    client = OpenAIResponsesClient(api_key=api_key, model=args.llm_model)
    return LLMResearchManager(client)


if __name__ == "__main__":
    raise SystemExit(main())
