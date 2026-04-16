"""Command-line interface for the stock research scaffold."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from dataclasses import dataclass, field
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


@dataclass
class InvestigationResult:
    ticker: str
    question: str
    artifact_dir: str | None
    outputs: dict[str, AgentEnvelope]
    llm_memo: str | None = None
    manager_steps: list[dict] = field(default_factory=list)
    agents_run: list[str] = field(default_factory=list)


@dataclass
class ChatResult:
    ticker: str
    question: str
    answer: str
    next_action: str | None = None
    used_llm: bool = False


@dataclass
class ShellSession:
    active_ticker: str | None = None
    active_model_provider: str = "openai"
    active_model_name: str = "gpt-5.4-mini"
    conversation_context: list[str] = field(default_factory=list)
    latest_run_id: str | None = None
    latest_decision: str | None = None
    latest_what_changed: str | None = None


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
        result = _execute_investigation(args)
    except (ConnectorError, LLMError) as exc:
        label = "LLM error" if isinstance(exc, LLMError) else "Connector error"
        print(f"{label}: {exc}")
        return 1

    if args.json:
        if result.llm_memo is not None:
            print(
                json.dumps(
                    {
                        "memo": result.llm_memo,
                        "agents_run": result.agents_run,
                        "plan_thought": result.manager_steps[0]["thought"] if result.manager_steps else "",
                        "loop_steps": result.manager_steps,
                    },
                    indent=2,
                )
            )
        else:
            print(json.dumps(_run_to_dict(result.outputs), indent=2))
        return 0

    _render_investigation_result(result, verbose=True)
    return 0


def _execute_investigation(args) -> InvestigationResult:
    try:
        connectors = _connector_bundle_from_args(args)
    except ConnectorError:
        raise
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
        manager = _llm_manager_from_args(args)
        loop = ManagerLoop(manager.llm_client)

        # Build source packets outside the orchestrator so the loop can use them.
        source_packets: dict = {}
        if connectors is not None:
            source_packets = {
                t: connectors.build_source_packet(t) for t in request.tickers
            }

        run_dir = run_store.start_run(request, list(ManagerLoop._PIPELINE_ORDER))
        if source_packets:
            run_store.record_source_packets(run_dir, source_packets)

        result = loop.run(
            request,
            agent_executor=runtime.execute,
            source_packets=source_packets,
            run_dir=run_dir,
            run_store=run_store,
        )

        # Persist the actual agent outputs so history / load_latest_outputs work.
        from .models import SourcePacket as _SP
        run_store.finish_run(
            run_dir,
            request=request,
            outputs=result.outputs,
            source_packets=source_packets or {ticker: _SP(ticker)},
            steps=result.agents_run,
        )
        return InvestigationResult(
            ticker=ticker,
            question=request.user_query,
            artifact_dir=str(run_dir),
            outputs=result.outputs,
            llm_memo=result.memo,
            manager_steps=result.loop_steps,
            agents_run=result.agents_run,
        )

    # ── Standard deterministic pipeline path ─────────────────────────────────
    orchestrator = InvestigationOrchestrator(connectors=connectors, run_store=run_store)
    run = orchestrator.run(request, agent_executor=runtime.execute)

    llm_memo: str | None = None

    if args.llm:
        manager = _llm_manager_from_args(args)
        llm_response = manager.compose_investigation_response(request, run.outputs)
        llm_memo = llm_response.text
        if run.artifact_dir is not None:
            run_store.record_llm_memo(
                run.artifact_dir,
                llm_response.text,
                model=llm_response.model,
                provider=llm_response.provider,
            )
    return InvestigationResult(
        ticker=ticker,
        question=request.user_query,
        artifact_dir=str(run.artifact_dir) if run.artifact_dir is not None else None,
        outputs=run.outputs,
        llm_memo=llm_memo,
        agents_run=run.steps,
    )


def _handle_chat(args) -> int:
    try:
        result = _execute_chat(args)
    except (ConnectorError, LLMError) as exc:
        label = "LLM error" if isinstance(exc, LLMError) else "Connector error"
        print(f"{label}: {exc}")
        return 1
    print(result.answer)
    if result.next_action:
        print(f"Next action: {result.next_action}")
    return 0


def _execute_chat(args) -> ChatResult:
    ticker = args.ticker.upper()
    connectors = _connector_bundle_from_args(args)
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
        run = orchestrator.run(refresh_request, agent_executor=runtime.execute)
        prior_research = run.outputs
        chat_run_dir = run.artifact_dir

    interface = ConversationalInterface()
    if args.llm and prior_research:
        manager = _llm_manager_from_args(args)
        llm_response = manager.answer_chat_response(request, prior_research)
        if chat_run_dir is not None:
            run_store.record_llm_chat(
                chat_run_dir,
                question=args.question,
                answer=llm_response.text,
                model=llm_response.model,
                provider=llm_response.provider,
            )
        return ChatResult(
            ticker=ticker,
            question=args.question,
            answer=llm_response.text,
            used_llm=True,
        )

    result = interface.respond(request, prior_research=prior_research)
    next_action = result.envelope.payload.get("recommended_next_action")
    return ChatResult(
        ticker=ticker,
        question=args.question,
        answer=result.answer,
        next_action=next_action,
        used_llm=False,
    )


def _run_to_dict(outputs: dict[str, AgentEnvelope]) -> dict[str, dict]:
    return {name: envelope.to_dict() for name, envelope in outputs.items()}


def _render_investigation_result(result: InvestigationResult, verbose: bool = True) -> None:
    if result.llm_memo is not None and result.manager_steps:
        print(f"Investigation (agentic): {result.ticker}")
        print(f"Question: {result.question}")
        if result.artifact_dir is not None:
            print(f"Run artifacts: {result.artifact_dir}")
        if result.manager_steps:
            first_plan = next((step for step in result.manager_steps if step.get("step") == "plan"), None)
            if first_plan is not None:
                print(f"\nPlanning thought: {first_plan.get('thought', '')}")
        print(f"Agents run: {', '.join(result.agents_run)}")
        if verbose:
            _print_manager_steps(result.manager_steps)
        print("\n[llm memo]")
        print(result.llm_memo)
        return

    print(f"Investigation: {result.ticker}")
    print(f"Question: {result.question}")
    if result.artifact_dir is not None:
        print(f"Run artifacts: {result.artifact_dir}")
    if not verbose:
        synth = result.outputs.get("synthesizer")
        if synth is not None:
            print(synth.summary)
            _print_synthesizer_sections(synth)
        elif result.llm_memo:
            print(result.llm_memo)
        return
    for agent_name in result.agents_run:
        output = result.outputs.get(agent_name)
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
    if result.llm_memo:
        print("\n[llm]")
        print(result.llm_memo)


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


def _shell_rules_text() -> str:
    return (
        "Templeton rules:\n"
        "- Use evidence-backed sources only.\n"
        "- Refresh for current, latest, price, or news-sensitive questions.\n"
        "- Say when evidence is stale, weak, or contradictory.\n"
        "- Preserve research continuity through memory and what-changed diffs."
    )


def _print_shell_memory(session: ShellSession) -> None:
    print("Session memory:")
    print(f"- Active ticker: {session.active_ticker or 'none'}")
    print(f"- Model: {session.active_model_provider}/{session.active_model_name}")
    print(f"- Latest decision: {session.latest_decision or 'none'}")
    print(f"- Latest what changed: {session.latest_what_changed or 'none'}")
    if session.conversation_context:
        print(f"- Recent context: {session.conversation_context[-1]}")


def _handle_shell_meta_command(tokens: list[str], session: ShellSession, run_store: LocalRunStore) -> bool:
    command = tokens[0]
    if command == "/help":
        print("Natural language handles research tasks.")
        print("/model [provider] [model]")
        print("/rules")
        print("/clear")
        print("/memory")
        print("/history [TICKER] [limit]")
        print("/quit")
        return True
    if command == "/rules":
        print(_shell_rules_text())
        return True
    if command == "/clear":
        session.active_ticker = None
        session.conversation_context.clear()
        session.latest_run_id = None
        session.latest_decision = None
        session.latest_what_changed = None
        print("Session context cleared.")
        return True
    if command == "/memory":
        _print_shell_memory(session)
        return True
    if command == "/history":
        ticker = session.active_ticker
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
            print("No active ticker. Ask about a ticker first or pass one explicitly.")
            return True
        _print_history(run_store, ticker, limit=limit)
        return True
    if command == "/model":
        if len(tokens) == 1:
            print(f"Current model: {session.active_model_provider}/{session.active_model_name}")
            return True
        if len(tokens) >= 2:
            session.active_model_provider = tokens[1]
        if len(tokens) >= 3:
            session.active_model_name = tokens[2]
        print(f"Model set to: {session.active_model_provider}/{session.active_model_name}")
        return True
    return False


def _extract_tickers(text: str) -> list[str]:
    found = re.findall(r"\b[A-Z]{1,5}\b", text)
    candidates: list[str] = []
    for token in found:
        if token.lower() in {
            "llm",
        }:
            continue
        if token not in candidates:
            candidates.append(token)
    return candidates


def _needs_refresh(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("refresh", "latest", "current", "today", "news", "price", "right now"))


def _wants_history(text: str) -> bool:
    lowered = text.lower()
    return "what changed" in lowered or "since last" in lowered or "history" in lowered


def _wants_compare(text: str) -> bool:
    lowered = text.lower()
    return "compare" in lowered or "versus" in lowered or " vs " in lowered


def _wants_investigation(text: str, prior_outputs: dict[str, AgentEnvelope]) -> bool:
    lowered = text.lower()
    if any(term in lowered for term in ("investigate", "look into", "analyze", "research", "worth buying", "should i buy")):
        return True
    return not prior_outputs


def _update_shell_session_from_outputs(session: ShellSession, result: InvestigationResult) -> None:
    session.active_ticker = result.ticker
    if result.artifact_dir is not None:
        session.latest_run_id = result.artifact_dir.rsplit("/", 1)[-1]
    decision = result.outputs.get("decision_portfolio_fit")
    if decision is not None:
        session.latest_decision = decision.payload.get("decision")
    synth = result.outputs.get("synthesizer")
    if synth is not None:
        session.latest_what_changed = synth.payload.get("memo_sections", {}).get("what_changed")


def _build_shell_args(base_args, ticker: str, *, query: str | None = None, refresh: bool = False):
    shell_args = argparse.Namespace(**vars(base_args))
    shell_args.ticker = ticker
    shell_args.query = query
    shell_args.question = query
    shell_args.refresh = refresh
    shell_args.time_horizon = "long_term"
    shell_args.objective = "long_term_compounding"
    shell_args.json = False
    shell_args.llm_provider = getattr(base_args, "llm_provider", "openai")
    shell_args.llm_model = getattr(base_args, "llm_model", "gpt-5.4-mini")
    return shell_args


def _handle_shell_natural_language(raw: str, session: ShellSession, base_args, run_store: LocalRunStore) -> None:
    tickers = _extract_tickers(raw)
    ticker = tickers[0] if tickers else session.active_ticker

    if _wants_compare(raw):
        if len(tickers) < 2:
            print("Comparison needs two tickers. Example: compare NVDA and AMD.")
            return
        print("Comparison routing is planned but not implemented yet. Ask for one name at a time for now.")
        return

    if _wants_history(raw):
        if not ticker:
            print("I need a ticker to show thesis history or what changed.")
            return
        _print_history(run_store, ticker, limit=5)
        session.active_ticker = ticker
        session.conversation_context.append(raw)
        return

    if not ticker:
        print("I need a ticker. Example: look into ASML for a 5 year hold.")
        return

    prior_outputs = run_store.load_latest_outputs(ticker)

    if _needs_refresh(raw):
        investigate_args = _build_shell_args(base_args, ticker, query=f"Investigate {ticker}")
        try:
            result = _execute_investigation(investigate_args)
        except (ConnectorError, LLMError) as exc:
            label = "LLM error" if isinstance(exc, LLMError) else "Connector error"
            print(f"{label}: {exc}")
            return
        _update_shell_session_from_outputs(session, result)
        session.conversation_context.append(raw)
        print(f"Refreshing {ticker} with current data.")
        _render_investigation_result(result, verbose=False)
        return

    if _wants_investigation(raw, prior_outputs):
        investigate_args = _build_shell_args(base_args, ticker, query=raw)
        try:
            result = _execute_investigation(investigate_args)
        except (ConnectorError, LLMError) as exc:
            label = "LLM error" if isinstance(exc, LLMError) else "Connector error"
            print(f"{label}: {exc}")
            return
        _update_shell_session_from_outputs(session, result)
        session.conversation_context.append(raw)
        _render_investigation_result(result, verbose=False)
        return

    chat_args = _build_shell_args(base_args, ticker, query=raw, refresh=False)
    try:
        result = _execute_chat(chat_args)
    except (ConnectorError, LLMError) as exc:
        label = "LLM error" if isinstance(exc, LLMError) else "Connector error"
        print(f"{label}: {exc}")
        return
    session.active_ticker = ticker
    session.conversation_context.append(raw)
    print(result.answer)
    if result.next_action:
        print(f"Next action: {result.next_action}")


def _handle_benchmark(args) -> int:
    harness = BenchmarkHarness(run_store=LocalRunStore(args.store_dir))
    result = harness.run_suite(args.suite)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print(format_suite_result(result))
    return 0


def _handle_shell(args) -> int:
    session = ShellSession(
        active_model_provider=args.llm_provider,
        active_model_name=args.llm_model,
    )
    run_store = LocalRunStore(args.store_dir)
    print("Templeton shell")
    print("Use natural language for research. Slash commands are for session control.")
    print("Commands: /model, /rules, /clear, /memory, /history, /help, /quit")
    while True:
        prompt = f"templeton[{session.active_ticker or '-'}]> "
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

        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            print(f"Input error: {exc}")
            continue
        if not tokens:
            continue

        command = tokens[0]
        if raw.startswith("/"):
            if not _handle_shell_meta_command(tokens, session, run_store):
                print(f"Unknown command: {command}")
            continue
        _handle_shell_natural_language(raw, session, args, run_store)


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
