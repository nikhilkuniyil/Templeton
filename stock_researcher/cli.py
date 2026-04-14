"""Command-line interface for the stock research scaffold."""

from __future__ import annotations

import argparse
import json
from uuid import uuid4

from .agents import AgentRuntime
from .conversation import ConversationalInterface
from .demo_data import demo_connector_bundle
from .models import AgentEnvelope, ResearchRequest
from .orchestrator import InvestigationOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="templeton", description="CLI for the stock research system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    investigate = subparsers.add_parser("investigate", help="Run the investigation workflow for a ticker")
    investigate.add_argument("ticker", help="Ticker symbol to investigate")
    investigate.add_argument("--query", default=None, help="Optional research question")
    investigate.add_argument("--time-horizon", default="long_term", help="Investment horizon label")
    investigate.add_argument("--objective", default="long_term_compounding", help="Research objective")
    investigate.add_argument("--json", action="store_true", help="Print raw JSON output")
    investigate.add_argument("--demo", action="store_true", help="Use built-in demo connector data")

    chat = subparsers.add_parser("chat", help="Ask a conversational research question")
    chat.add_argument("ticker", help="Ticker symbol to discuss")
    chat.add_argument("question", help="Question to ask")
    chat.add_argument("--demo", action="store_true", help="Use built-in demo connector data")
    chat.add_argument("--refresh", action="store_true", help="Run a fresh investigation before answering")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "investigate":
        return _handle_investigate(args)
    if args.command == "chat":
        return _handle_chat(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _handle_investigate(args) -> int:
    runtime = AgentRuntime()
    connectors = demo_connector_bundle() if args.demo else None
    orchestrator = InvestigationOrchestrator(connectors=connectors)
    ticker = args.ticker.upper()
    request = ResearchRequest(
        request_id=f"req_{uuid4().hex[:8]}",
        user_query=args.query or f"Investigate {ticker}",
        mode="investigation",
        tickers=[ticker],
        time_horizon=args.time_horizon,
        objective=args.objective,
    )
    run = orchestrator.run(request, agent_executor=runtime.execute)

    if args.json:
        print(json.dumps(_run_to_dict(run.outputs), indent=2))
        return 0

    print(f"Investigation: {ticker}")
    print(f"Question: {request.user_query}")
    for agent_name in run.steps:
        output = run.outputs.get(agent_name)
        if output is None:
            continue
        print(f"\n[{agent_name}]")
        print(output.summary)
        if output.key_points:
            for point in output.key_points[:3]:
                print(f"- {point}")
    return 0


def _handle_chat(args) -> int:
    ticker = args.ticker.upper()
    runtime = AgentRuntime()
    connectors = demo_connector_bundle() if args.demo else None
    orchestrator = InvestigationOrchestrator(connectors=connectors)
    request = ResearchRequest(
        request_id=f"req_{uuid4().hex[:8]}",
        user_query=args.question,
        mode="conversation",
        tickers=[ticker],
    )
    prior_research: dict[str, AgentEnvelope] = {}
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

    interface = ConversationalInterface()
    result = interface.respond(request, prior_research=prior_research)
    print(result.answer)

    next_action = result.envelope.payload.get("recommended_next_action")
    if next_action:
        print(f"Next action: {next_action}")
    return 0


def _run_to_dict(outputs: dict[str, AgentEnvelope]) -> dict[str, dict]:
    return {name: envelope.to_dict() for name, envelope in outputs.items()}


if __name__ == "__main__":
    raise SystemExit(main())
