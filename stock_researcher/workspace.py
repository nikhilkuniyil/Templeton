"""Persistent investor workspace for watchlists, portfolio context, dossiers, and notes."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .models import AgentEnvelope


class WorkspaceStore:
    """Stores durable investor-workspace objects under the local store directory."""

    def __init__(self, base_dir: str | Path = ".templeton") -> None:
        self.base_dir = Path(base_dir)
        self.workspace_dir = self.base_dir / "workspace"
        self.watchlists_path = self.workspace_dir / "watchlists.json"
        self.portfolios_path = self.workspace_dir / "portfolios.json"
        self.dossiers_path = self.workspace_dir / "dossiers.json"
        self.notes_path = self.workspace_dir / "notes.json"

    def add_to_watchlist(self, name: str, ticker: str, reason: str | None = None) -> dict:
        payload = self._read_json(self.watchlists_path, {"watchlists": {}})
        key = self._normalize_name(name)
        watchlists = payload["watchlists"]
        watchlist = watchlists.setdefault(
            key,
            {
                "watchlist_id": key,
                "name": name.strip(),
                "description": "",
                "tags": [],
                "tickers": [],
                "entries": {},
                "ranking_method": "readiness",
                "updated_at": self._now(),
            },
        )
        ticker = ticker.upper()
        if ticker not in watchlist["tickers"]:
            watchlist["tickers"].append(ticker)
        watchlist["entries"][ticker] = {
            "ticker": ticker,
            "added_at": self._now(),
            "reason": reason,
        }
        watchlist["updated_at"] = self._now()
        self._write_json(self.watchlists_path, payload)

        dossier = self.get_or_create_dossier(ticker)
        if key not in dossier["watchlists"]:
            dossier["watchlists"].append(key)
        dossier["updated_at"] = self._now()
        self._save_dossier(dossier)
        return watchlist

    def get_watchlist(self, name: str) -> dict | None:
        payload = self._read_json(self.watchlists_path, {"watchlists": {}})
        key = self._normalize_name(name)
        watchlist = payload["watchlists"].get(key)
        if watchlist is not None:
            return watchlist
        for candidate in payload["watchlists"].values():
            if candidate["name"].lower() == name.strip().lower():
                return candidate
        return None

    def list_watchlists(self) -> list[dict]:
        payload = self._read_json(self.watchlists_path, {"watchlists": {}})
        watchlists = list(payload["watchlists"].values())
        return sorted(watchlists, key=lambda item: item["name"].lower())

    def rank_watchlist(self, name: str) -> dict | None:
        watchlist = self.get_watchlist(name)
        if watchlist is None:
            return None
        dossiers = self._read_json(self.dossiers_path, {"dossiers": {}})["dossiers"]
        entries: list[dict] = []
        for ticker in watchlist.get("tickers", []):
            dossier = dossiers.get(ticker, {})
            readiness_score = self._readiness_score(dossier)
            entries.append(
                {
                    "ticker": ticker,
                    "decision": dossier.get("latest_decision"),
                    "confidence": dossier.get("latest_confidence"),
                    "readiness_score": readiness_score,
                    "readiness_status": self._readiness_status(readiness_score),
                    "what_changed": dossier.get("what_changed"),
                    "top_reason": dossier.get("top_reason"),
                    "open_questions": dossier.get("open_questions", []),
                    "key_risks": dossier.get("key_risks", []),
                }
            )
        entries.sort(key=lambda item: (-item["readiness_score"], item["ticker"]))
        return {
            "watchlist_id": watchlist["watchlist_id"],
            "name": watchlist["name"],
            "entries": entries,
            "updated_at": watchlist.get("updated_at"),
        }

    def add_position(self, ticker: str, note: str | None = None) -> dict:
        payload = self._ensure_default_portfolio()
        portfolio = payload["portfolios"]["default"]
        ticker = ticker.upper()
        portfolio["positions"][ticker] = {
            "ticker": ticker,
            "added_at": self._now(),
            "note": note,
            "themes": self.themes_for_ticker(ticker),
        }
        portfolio["updated_at"] = self._now()
        self._write_json(self.portfolios_path, payload)
        return portfolio

    def add_priority_theme(self, theme: str) -> dict:
        payload = self._ensure_default_portfolio()
        portfolio = payload["portfolios"]["default"]
        normalized = theme.strip().lower()
        if normalized and normalized not in portfolio["priority_themes"]:
            portfolio["priority_themes"].append(normalized)
        portfolio["updated_at"] = self._now()
        self._write_json(self.portfolios_path, payload)
        return portfolio

    def get_default_portfolio(self) -> dict:
        payload = self._ensure_default_portfolio()
        return payload["portfolios"]["default"]

    def save_note(
        self,
        body: str,
        *,
        scope_type: str,
        scope_id: str,
        ticker: str | None = None,
        watchlist: str | None = None,
    ) -> dict:
        payload = self._read_json(self.notes_path, {"notes": []})
        note = {
            "note_id": f"note_{uuid4().hex[:8]}",
            "scope_type": scope_type,
            "scope_id": scope_id,
            "body": body.strip(),
            "created_at": self._now(),
            "ticker": ticker.upper() if ticker else None,
            "watchlist": self._normalize_name(watchlist) if watchlist else None,
        }
        payload["notes"].append(note)
        self._write_json(self.notes_path, payload)
        if ticker:
            dossier = self.get_or_create_dossier(ticker)
            if note["note_id"] not in dossier["note_ids"]:
                dossier["note_ids"].append(note["note_id"])
            dossier["updated_at"] = self._now()
            self._save_dossier(dossier)
        return note

    def notes_for_scope(self, scope_type: str, scope_id: str) -> list[dict]:
        payload = self._read_json(self.notes_path, {"notes": []})
        return [
            note
            for note in payload["notes"]
            if note["scope_type"] == scope_type and note["scope_id"] == scope_id
        ]

    def notes_for_ticker(self, ticker: str) -> list[dict]:
        payload = self._read_json(self.notes_path, {"notes": []})
        return [note for note in payload["notes"] if note.get("ticker") == ticker.upper()]

    def get_or_create_dossier(self, ticker: str) -> dict:
        ticker = ticker.upper()
        payload = self._read_json(self.dossiers_path, {"dossiers": {}})
        dossiers = payload["dossiers"]
        dossier = dossiers.setdefault(
            ticker,
            {
                "ticker": ticker,
                "latest_decision": None,
                "latest_confidence": None,
                "latest_memo_run_id": None,
                "thesis_status": "unresearched",
                "thesis_summary": None,
                "valuation_view": None,
                "what_changed": None,
                "top_reason": None,
                "open_questions": [],
                "key_risks": [],
                "monitoring_items": [],
                "watchlists": [],
                "note_ids": [],
                "updated_at": self._now(),
            },
        )
        self._write_json(self.dossiers_path, payload)
        return dossier

    def update_dossier_from_outputs(
        self,
        ticker: str,
        outputs: dict[str, AgentEnvelope],
        run_id: str | None,
    ) -> dict:
        ticker = ticker.upper()
        payload = self._read_json(self.dossiers_path, {"dossiers": {}})
        dossiers = payload["dossiers"]
        dossier = dossiers.setdefault(ticker, self.get_or_create_dossier(ticker))

        decision = outputs.get("decision_portfolio_fit")
        synthesizer = outputs.get("synthesizer")
        valuation = outputs.get("valuation")
        risk = outputs.get("risk")

        if decision is not None:
            dossier["latest_decision"] = decision.payload.get("decision")
            dossier["latest_confidence"] = decision.payload.get("confidence", decision.confidence)
            key_reasons = decision.payload.get("key_reasons", [])
            dossier["top_reason"] = key_reasons[0] if key_reasons else decision.summary
        if synthesizer is not None:
            sections = synthesizer.payload.get("memo_sections", {})
            dossier["latest_memo_run_id"] = run_id
            dossier["thesis_summary"] = synthesizer.summary
            dossier["what_changed"] = sections.get("what_changed")
        if valuation is not None:
            dossier["valuation_view"] = valuation.payload.get("valuation_label")
        if risk is not None:
            dossier["key_risks"] = self._normalize_text_items(risk.payload.get("core_risks", []))[:3]
            dossier["monitoring_items"] = self._normalize_text_items(risk.payload.get("monitoring_indicators", []))[:5]

        open_questions: list[str] = []
        for envelope in outputs.values():
            open_questions.extend(envelope.open_questions)
        dossier["open_questions"] = sorted(set(question for question in open_questions if question))[:6]
        dossier["thesis_status"] = self._readiness_status(self._readiness_score(dossier))
        dossier["updated_at"] = self._now()

        self._write_json(self.dossiers_path, payload)
        return dossier

    def summarize_portfolio(self) -> dict:
        portfolio = self.get_default_portfolio()
        positions = portfolio.get("positions", {})
        position_themes: dict[str, int] = {}
        for position in positions.values():
            for theme in position.get("themes", []):
                position_themes[theme] = position_themes.get(theme, 0) + 1
        priority_themes = portfolio.get("priority_themes", [])
        underweight = [
            theme for theme in priority_themes
            if position_themes.get(theme, 0) == 0
        ]
        return {
            "portfolio": portfolio,
            "position_count": len(positions),
            "position_themes": position_themes,
            "priority_themes": priority_themes,
            "underweight_themes": underweight,
        }

    def allocation_view(self, theme: str | None = None) -> dict:
        summary = self.summarize_portfolio()
        watchlists = self.list_watchlists()
        candidates: list[dict] = []
        target_theme = theme.strip().lower() if theme else None
        for watchlist in watchlists:
            if target_theme and target_theme not in watchlist["name"].lower():
                continue
            ranked = self.rank_watchlist(watchlist["name"])
            if ranked is None:
                continue
            for entry in ranked["entries"]:
                entry_copy = dict(entry)
                entry_copy["watchlist"] = ranked["name"]
                candidates.append(entry_copy)
        candidates.sort(key=lambda item: (-item["readiness_score"], item["ticker"]))
        return {
            "theme": target_theme,
            "priority_themes": summary["priority_themes"],
            "underweight_themes": summary["underweight_themes"],
            "candidates": candidates[:5],
        }

    def workspace_summary(self) -> dict:
        watchlists = self.list_watchlists()
        portfolio = self.get_default_portfolio()
        dossiers = self._read_json(self.dossiers_path, {"dossiers": {}})["dossiers"]
        notes = self._read_json(self.notes_path, {"notes": []})["notes"]
        return {
            "watchlist_count": len(watchlists),
            "portfolio_position_count": len(portfolio.get("positions", {})),
            "priority_themes": portfolio.get("priority_themes", []),
            "dossier_count": len(dossiers),
            "note_count": len(notes),
        }

    def themes_for_ticker(self, ticker: str) -> list[str]:
        themes: list[str] = []
        for watchlist in self.list_watchlists():
            if ticker.upper() in watchlist.get("tickers", []):
                normalized = self._normalize_name(watchlist["name"])
                if normalized not in themes:
                    themes.append(normalized)
        return themes

    def _ensure_default_portfolio(self) -> dict:
        payload = self._read_json(self.portfolios_path, {"portfolios": {}})
        payload["portfolios"].setdefault(
            "default",
            {
                "portfolio_id": "default",
                "name": "default",
                "positions": {},
                "cash_available": None,
                "bucket_targets": {},
                "risk_limits": {},
                "priority_themes": [],
                "updated_at": self._now(),
            },
        )
        self._write_json(self.portfolios_path, payload)
        return payload

    def _save_dossier(self, dossier: dict) -> None:
        payload = self._read_json(self.dossiers_path, {"dossiers": {}})
        payload["dossiers"][dossier["ticker"]] = dossier
        self._write_json(self.dossiers_path, payload)

    def _readiness_score(self, dossier: dict) -> int:
        decision = dossier.get("latest_decision")
        confidence = dossier.get("latest_confidence")
        score = 0
        if decision == "buy":
            score += 60
        elif decision == "watch":
            score += 35
        elif decision == "pass":
            score += 10

        if confidence == "high":
            score += 25
        elif confidence == "medium":
            score += 15
        elif confidence == "low":
            score += 5

        score -= min(len(dossier.get("open_questions", [])) * 5, 20)
        return max(score, 0)

    def _readiness_status(self, score: int) -> str:
        if score >= 70:
            return "ready"
        if score >= 40:
            return "building"
        if score > 0:
            return "early"
        return "unresearched"

    def _normalize_name(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
        return normalized.strip("_") or "default"

    def _normalize_text_items(self, items: list) -> list[str]:
        normalized: list[str] = []
        for item in items:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
                continue
            if isinstance(item, dict):
                for key in ("risk", "indicator", "item", "name", "summary"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        normalized.append(value.strip())
                        break
        return normalized

    def _read_json(self, path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()
