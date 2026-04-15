"""Command-line interface for the stock research scaffold."""

from __future__ import annotations

import argparse
import json
import os
import shlex
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
from .llm import AnthropicMessagesClient, GeminiGenerateContentClient
from .models import AgentEnvelope, ResearchRequest
from .orchestrator import InvestigationOrchestrator
from .research_manager import LLMResearchManager, ManagerLoop
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
    investigate.add_argument(
        "--llm-provider",
        default="openai",
        choices=["openai", "anthropic", "gemini"],
        help="LLM provider to use when --llm is enabled",
    )
    investigate.add_argument("--llm-model", default="gpt-5.4-mini", help="LLM model to use when --llm is enabled")
    investigate.add_argument(
        "--agentic",
        action="store_true",
        help="Use the LLM manager loop: LLM plans which agents to run, executes them, then synthesizes (requires --llm)",
    )
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
    chat.add_argument(
        "--llm-provider",
        default="openai",
        choices=["openai", "anthropic", "gemini"],
        help="LLM provider to use when --llm is enabled",
    )
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

    shell = subparsers.add_parser("shell", help="Launch an interactive Templeton terminal")
    shell.add_argument("--llm", action="store_true", help="Use an LLM for upgraded memos and chat")
    shell.add_argument(
        "--llm-provider",
        default="openai",
        choices=["openai", "anthropic", "gemini"],
        help="LLM provider to use when --llm is enabled",
    )
    shell.add_argument("--llm-model", default="gpt-5.4-mini", help="LLM model to use when --llm is enabled")
    shell.add_argument(
        "--agentic",
        action="store_true",
        help="Use the iterative LLM manager loop for investigations in shell mode",
    )
    shell.add_argument("--demo", action="store_true", help="Use built-in demo connector data")
    shell.add_argument("--live-filings", action="store_true", help="Use live SEC filings with market/news connectors")
    shell.add_argument(
        "--financial-datasets",
        action="store_true",
        help="Use Financial Datasets as the primary structured-data backbone",
    )
    shell.add_argument(
        "--store-dir",
        default=".templeton",
        help="Local directory for run artifacts and history",
    )
    shell.add_argument(
        "--sec-user-agent",
        default="TempletonResearch/0.1 (contact: local@example.com)",
        help="User-Agent header for SEC requests",
    )

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
    if args.command == "shell":
        return _handle_shell(args)
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
    ticker = args.ticker.upper()
    request = ResearchRequest(
        request_id=f"req_{uuid4().hex[:8]}",
        user_query=args.query or f"Investigate {ticker}",
        mode="investigation",
        tickers=[ticker],
        time_horizon=args.time_horizon,
        objective=args.objective,
    )

    # ── Agentic loop path (--agentic implies --llm) ───────────────────────────
    if getattr(args, "agentic", False):
        try:
            manager = _llm_manager_from_args(args)
        except ConnectorError as exc:
            print(f"LLM setup error: {exc}")
            return 1
        loop = ManagerLoop(manager.llm_client)

        # Build source packets outside the orchestrator so the loop can use them.
        source_packets: dict = {}
        if connectors is not None:
            try:
                source_packets = {
                    t: connectors.build_source_packet(t) for t in request.tickers
                }
            except ConnectorError as exc:
                print(f"Connector error: {exc}")
                return 1

        run_dir = run_store.start_run(request, list(ManagerLoop._PIPELINE_ORDER))
        if source_packets:
            run_store.record_source_packets(run_dir, source_packets)

        try:
            result = loop.run(
                request,
                agent_executor=runtime.execute,
                source_packets=source_packets,
                run_dir=run_dir,
                run_store=run_store,
            )
        except LLMError as exc:
            print(f"LLM error: {exc}")
            return 1

        # Persist the actual agent outputs so history / load_latest_outputs work.
        from .models import SourcePacket as _SP
        run_store.finish_run(
            run_dir,
            request=request,
            outputs=result.outputs,
            source_packets=source_packets or {ticker: _SP(ticker)},
            steps=result.agents_run,
        )

        if args.json:
            print(
                json.dumps(
                    {
                        "memo": result.memo,
                        "agents_run": result.agents_run,
                        "plan_thought": result.plan_thought,
                        "loop_steps": result.loop_steps,
                    },
                    indent=2,
                )
            )
            return 0

        print(f"Investigation (agentic): {ticker}")
        print(f"Question: {request.user_query}")
        print(f"Run artifacts: {run_dir}")
        print(f"\nPlanning thought: {result.plan_thought}")
        print(f"Agents run: {', '.join(result.agents_run)}")
        _print_manager_steps(result.loop_steps)
        print("\n[llm memo]")
        print(result.memo)
        return 0

    # ── Standard deterministic pipeline path ─────────────────────────────────
    orchestrator = InvestigationOrchestrator(connectors=connectors, run_store=run_store)
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
            llm_response = manager.compose_investigation_response(request, run.outputs)
        except (ConnectorError, LLMError) as exc:
            print(f"\n[llm]\nLLM error: {exc}")
            return 1
        print("\n[llm]")
        print(llm_response.text)
        if run.artifact_dir is not None:
            run_store.record_llm_memo(
                run.artifact_dir,
                llm_response.text,
                model=llm_response.model,
                provider=llm_response.provider,
            )
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
    chat_run_dir = run_store.latest_run_dir(ticker)
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
        chat_run_dir = run.artifact_dir

    interface = ConversationalInterface()
    if args.llm and prior_research:
        try:
            manager = _llm_manager_from_args(args)
            llm_response = manager.answer_chat_response(request, prior_research)
        except (ConnectorError, LLMError) as exc:
            print(f"LLM error: {exc}")
            return 1
        print(llm_response.text)
        if chat_run_dir is not None:
            run_store.record_llm_chat(
                chat_run_dir,
                question=args.question,
                answer=llm_response.text,
                model=llm_response.model,
                provider=llm_response.provider,
            )
        return 0

    result = interface.respond(request, prior_research=prior_research)
    print(result.answer)

    next_action = result.envelope.payload.get("recommended_next_action")
    if next_action:
        print(f"Next action: {next_action}")
    return 0


def _run_to_dict(outputs: dict[str, AgentEnvelope]) -> dict[str, dict]:
    return {name: envelope.to_dict() for name, envelope in outputs.items()}


def _print_manager_steps(loop_steps: list[dict]) -> None:
    printable = [step for step in loop_steps if step.get("step") in {"manager_action", "manager_finalize"}]
    if not printable:
        return
    print("\nManager loop:")
    for step in printable:
        if step["step"] == "manager_action":
            print(f"- Run {step.get('agent')}: {step.get('thought', '')}")
        else:
            print(f"- Finalize: {step.get('thought', '')}")


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


def _print_history(run_store: LocalRunStore, ticker: str, limit: int = 5) -> None:
    entries = run_store.load_history_entries(ticker, limit=limit)
    if not entries:
        print(f"No saved history for {ticker}.")
        return
    print(f"History: {ticker}")
    for entry in entries:
        decision = (entry.get("decision") or "unknown").upper()
        freshness = entry.get("freshness_status") or "unknown"
        changed = entry.get("what_changed") or "No stored thesis diff."
        print(f"- {entry.get('saved_at')}: {decision} | freshness={freshness}")
        print(f"  {changed}")


def _handle_benchmark(args) -> int:
    harness = BenchmarkHarness(run_store=LocalRunStore(args.store_dir))
    result = harness.run_suite(args.suite)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print(format_suite_result(result))
    return 0


def _handle_shell(args) -> int:
    run_store = LocalRunStore(args.store_dir)
    active_ticker: str | None = None
    print("Templeton shell")
    print("Commands: /use TICKER, /investigate [TICKER] [query], /chat [TICKER] question, /refresh [TICKER], /history [TICKER] [limit], /help, /quit")
    while True:
        prompt = f"templeton[{active_ticker or '-'}]> "
        try:
            raw = input(prompt).strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 0

        if not raw:
            continue
        if raw in {"/quit", "/exit"}:
            return 0
        if raw == "/help":
            print("Free-form text asks a chat question about the active ticker.")
            print("/use TICKER")
            print("/investigate [TICKER] [optional query]")
            print("/chat [TICKER] question")
            print("/refresh [TICKER]")
            print("/history [TICKER] [limit]")
            print("/quit")
            continue

        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            print(f"Input error: {exc}")
            continue
        if not tokens:
            continue

        command = tokens[0]
        if command == "/use":
            if len(tokens) < 2:
                print("Usage: /use TICKER")
                continue
            active_ticker = tokens[1].upper()
            print(f"Active ticker: {active_ticker}")
            continue

        if command == "/history":
            ticker = active_ticker
            limit = 5
            if len(tokens) >= 2:
                maybe_limit = tokens[-1]
                if maybe_limit.isdigit():
                    limit = int(maybe_limit)
                    if len(tokens) >= 3:
                        ticker = tokens[1].upper()
                else:
                    ticker = tokens[1].upper()
            if not ticker:
                print("No active ticker. Use /use TICKER or pass one explicitly.")
                continue
            _print_history(run_store, ticker, limit=limit)
            continue

        if command == "/investigate":
            ticker = active_ticker
            query = None
            if len(tokens) >= 2:
                if tokens[1].isalnum() and len(tokens[1]) <= 10:
                    ticker = tokens[1].upper()
                    query = " ".join(tokens[2:]) or None
                else:
                    query = " ".join(tokens[1:]) or None
            if not ticker:
                print("No active ticker. Use /use TICKER or pass a ticker to /investigate.")
                continue
            active_ticker = ticker
            investigate_args = argparse.Namespace(**vars(args))
            investigate_args.command = "investigate"
            investigate_args.ticker = ticker
            investigate_args.query = query
            investigate_args.time_horizon = "long_term"
            investigate_args.objective = "long_term_compounding"
            investigate_args.json = False
            _handle_investigate(investigate_args)
            continue

        if command == "/refresh":
            ticker = active_ticker
            if len(tokens) >= 2:
                ticker = tokens[1].upper()
            if not ticker:
                print("No active ticker. Use /use TICKER or pass a ticker to /refresh.")
                continue
            active_ticker = ticker
            refresh_args = argparse.Namespace(**vars(args))
            refresh_args.command = "investigate"
            refresh_args.ticker = ticker
            refresh_args.query = f"Investigate {ticker}"
            refresh_args.time_horizon = "long_term"
            refresh_args.objective = "long_term_compounding"
            refresh_args.json = False
            _handle_investigate(refresh_args)
            continue

        if command == "/chat":
            ticker = active_ticker
            question_tokens = tokens[1:]
            if len(tokens) >= 3 and tokens[1].isalnum() and len(tokens[1]) <= 10:
                ticker = tokens[1].upper()
                question_tokens = tokens[2:]
            if not ticker:
                print("No active ticker. Use /use TICKER or pass a ticker to /chat.")
                continue
            if not question_tokens:
                print("Usage: /chat [TICKER] question")
                continue
            active_ticker = ticker
            chat_args = argparse.Namespace(**vars(args))
            chat_args.command = "chat"
            chat_args.ticker = ticker
            chat_args.question = " ".join(question_tokens)
            chat_args.refresh = False
            _handle_chat(chat_args)
            continue

        if raw.startswith("/"):
            print(f"Unknown command: {command}")
            continue

        if not active_ticker:
            print("No active ticker. Use /use TICKER or start with /investigate TICKER.")
            continue
        chat_args = argparse.Namespace(**vars(args))
        chat_args.command = "chat"
        chat_args.ticker = active_ticker
        chat_args.question = raw
        chat_args.refresh = False
        _handle_chat(chat_args)


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
    provider = args.llm_provider
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConnectorError("OPENAI_API_KEY is not set. Export it before using --llm with OpenAI.")
        client = OpenAIResponsesClient(api_key=api_key, model=args.llm_model)
        return LLMResearchManager(client)
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ConnectorError("ANTHROPIC_API_KEY is not set. Export it before using --llm with Anthropic.")
        client = AnthropicMessagesClient(api_key=api_key, model=args.llm_model)
        return LLMResearchManager(client)
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ConnectorError("GEMINI_API_KEY is not set. Export it before using --llm with Gemini.")
        client = GeminiGenerateContentClient(api_key=api_key, model=args.llm_model)
        return LLMResearchManager(client)
    raise ConnectorError(f"Unsupported LLM provider: {provider}")


if __name__ == "__main__":
    raise SystemExit(main())
