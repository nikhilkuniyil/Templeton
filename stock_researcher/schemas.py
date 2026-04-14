"""Helpers for loading JSON schemas from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def schema_path(name: str) -> Path:
    return SCHEMA_DIR / f"{name}.schema.json"


def load_schema(name: str) -> dict[str, Any]:
    with schema_path(name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def available_schemas() -> list[str]:
    return sorted(path.name.removesuffix(".schema.json") for path in SCHEMA_DIR.glob("*.schema.json"))
