"""Persist and load country data cache."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "countries_seed.json"
CACHE_PATH = ROOT / "data" / "cache.json"
TMP_CACHE_PATH = Path("/tmp/death_cache.json")


def _cache_path() -> Path:
    if os.environ.get("VERCEL"):
        return TMP_CACHE_PATH
    return CACHE_PATH


def load_cache() -> dict[str, Any]:
    path = _cache_path()
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    if SEED_PATH.exists():
        with SEED_PATH.open(encoding="utf-8") as f:
            return json.load(f)

    return {"updated_at": None, "countries": {}}


def save_cache(data: dict[str, Any]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_country(code: str) -> dict[str, Any] | None:
    cache = load_cache()
    return cache.get("countries", {}).get(code.upper())


def list_countries() -> list[dict[str, Any]]:
    cache = load_cache()
    countries = cache.get("countries", {})
    return sorted(
        [
            {
                "code": code,
                "name": info.get("name", code),
                "life_expectancy": (
                    round(info["life_expectancy"])
                    if info.get("life_expectancy") is not None
                    else None
                ),
                "region": info.get("region"),
            }
            for code, info in countries.items()
        ],
        key=lambda c: c["name"],
    )


def merge_country(code: str, payload: dict[str, Any]) -> None:
    cache = load_cache()
    countries = cache.setdefault("countries", {})
    existing = countries.get(code.upper(), {})
    existing.update(payload)
    existing["code"] = code.upper()
    countries[code.upper()] = existing
    cache["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_cache(cache)
