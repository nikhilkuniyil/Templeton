"""Local run storage and scratchpad logging for repeatable research."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import AgentEnvelope, ResearchRequest, SourcePacket


class LocalRunStore:
    """Persists investigation artifacts in a lightweight local directory structure."""

    def __init__(self, base_dir: str | Path = ".templeton") -> None:
        self.base_dir = Path(base_dir)

    def start_run(self, request: ResearchRequest, steps: list[str]) -> Path:
        run_dir = self.base_dir / "runs" / request.request_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(run_dir / "request.json", request.to_dict())
        self._write_json(run_dir / "plan.json", {"steps": steps})
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "init",
                "timestamp": self._now(),
                "request": request.to_dict(),
                "steps": steps,
            },
        )
        return run_dir

    def record_source_packets(self, run_dir: Path, source_packets: dict[str, SourcePacket]) -> None:
        serialized = {ticker: packet.to_dict() for ticker, packet in source_packets.items()}
        self._write_json(run_dir / "source_packets.json", serialized)
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "source_packets",
                "timestamp": self._now(),
                "tickers": list(source_packets.keys()),
                "document_counts": {
                    ticker: {
                        "filings": len(packet.filings),
                        "market_data": len(packet.market_data),
                        "news": len(packet.news),
                    }
                    for ticker, packet in source_packets.items()
                },
            },
        )

    def record_agent_output(self, run_dir: Path, envelope: AgentEnvelope) -> None:
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "agent_output",
                "timestamp": self._now(),
                "agent_name": envelope.agent_name,
                "ticker": envelope.ticker,
                "summary": envelope.summary,
                "confidence": envelope.confidence,
                "evidence_ids": envelope.evidence_ids,
            },
        )

    def finish_run(
        self,
        run_dir: Path,
        request: ResearchRequest,
        outputs: dict[str, AgentEnvelope],
        source_packets: dict[str, SourcePacket],
        steps: list[str],
    ) -> None:
        serialized_outputs = {name: envelope.to_dict() for name, envelope in outputs.items()}
        self._write_json(run_dir / "outputs.json", serialized_outputs)
        self._write_json(
            run_dir / "run.json",
            {
                "request_id": request.request_id,
                "mode": request.mode,
                "tickers": request.tickers,
                "steps": steps,
                "completed_agents": list(outputs.keys()),
                "saved_at": self._now(),
            },
        )
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "run_completed",
                "timestamp": self._now(),
                "completed_agents": list(outputs.keys()),
                "tickers": request.tickers,
            },
        )
        self._update_history(request, outputs, source_packets, run_dir)

    def load_latest_outputs(self, ticker: str) -> dict[str, AgentEnvelope]:
        history_path = self.base_dir / "history" / f"{ticker.upper()}.jsonl"
        if not history_path.exists():
            return {}
        entries = [
            json.loads(line)
            for line in history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not entries:
            return {}
        latest = entries[-1]
        run_dir = Path(latest["run_dir"])
        outputs_path = run_dir / "outputs.json"
        if not outputs_path.exists():
            return {}
        payload = json.loads(outputs_path.read_text(encoding="utf-8"))
        return {name: AgentEnvelope(**envelope) for name, envelope in payload.items()}

    def latest_run_dir(self, ticker: str) -> Path | None:
        history_path = self.base_dir / "history" / f"{ticker.upper()}.jsonl"
        if not history_path.exists():
            return None
        lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        entry = json.loads(lines[-1])
        return Path(entry["run_dir"])

    def _update_history(
        self,
        request: ResearchRequest,
        outputs: dict[str, AgentEnvelope],
        source_packets: dict[str, SourcePacket],
        run_dir: Path,
    ) -> None:
        decision = outputs.get("decision_portfolio_fit")
        source_verification = outputs.get("source_verification")
        synthesizer = outputs.get("synthesizer")
        history_dir = self.base_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        for ticker in request.tickers:
            self._append_jsonl(
                history_dir / f"{ticker.upper()}.jsonl",
                {
                    "request_id": request.request_id,
                    "run_dir": str(run_dir),
                    "saved_at": self._now(),
                    "ticker": ticker,
                    "decision": (
                        decision.payload.get("decision")
                        if decision is not None
                        else None
                    ),
                    "freshness_status": (
                        source_verification.payload.get("freshness_status")
                        if source_verification is not None
                        else None
                    ),
                    "memo_summary": synthesizer.summary if synthesizer is not None else None,
                    "memo_confidence": (
                        synthesizer.payload.get("confidence")
                        if synthesizer is not None
                        else None
                    ),
                    "what_changed": (
                        synthesizer.payload.get("memo_sections", {}).get("what_changed")
                        if synthesizer is not None
                        else None
                    ),
                    "source_counts": {
                        "filings": len(source_packets.get(ticker, SourcePacket(ticker)).filings),
                        "market_data": len(source_packets.get(ticker, SourcePacket(ticker)).market_data),
                        "news": len(source_packets.get(ticker, SourcePacket(ticker)).news),
                    },
                },
            )

    def record_llm_memo(
        self,
        run_dir: Path,
        text: str,
        model: str,
        provider: str,
        mode: str = "investigation",
    ) -> None:
        """Persist an LLM-generated memo to the run directory."""
        (run_dir / "llm_memo.md").write_text(text, encoding="utf-8")
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "llm_memo",
                "timestamp": self._now(),
                "mode": mode,
                "model": model,
                "provider": provider,
                "text_length": len(text),
            },
        )

    def record_llm_chat(
        self,
        run_dir: Path,
        question: str,
        answer: str,
        model: str,
        provider: str,
    ) -> None:
        """Append an LLM chat Q&A pair to the run's chat log."""
        entry = {
            "timestamp": self._now(),
            "question": question,
            "answer": answer,
            "model": model,
            "provider": provider,
        }
        self._append_jsonl(run_dir / "chat_log.jsonl", entry)
        self._append_jsonl(
            run_dir / "scratchpad.jsonl",
            {
                "type": "llm_chat",
                "timestamp": entry["timestamp"],
                "model": model,
                "provider": provider,
                "answer_length": len(answer),
            },
        )

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()
