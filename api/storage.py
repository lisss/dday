"""Persist and load country data cache."""

from __future__ import annotations

import json
import math
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


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("countries"), dict):
        return None
    return data


def load_cache() -> dict[str, Any]:
    cache_file = _cache_path()
    if cache_file.exists():
        data = _read_json_file(cache_file)
        if data is not None:
            return data

    if SEED_PATH.exists():
        data = _read_json_file(SEED_PATH)
        if data is not None:
            return data

    return {"updated_at": None, "countries": {}}


def save_cache(data: dict[str, Any]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _safe_life_expectancy_years(value: Any) -> int | None:
    if value is None:
        return None
    try:
        years = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(years):
        return None
    return round(years)


def get_country(code: str) -> dict[str, Any] | None:
    cache = load_cache()
    info = cache.get("countries", {}).get(code.upper())
    if not info or not isinstance(info, dict):
        return None
    result = dict(info)
    if "life_expectancy" in result:
        result["life_expectancy"] = _safe_life_expectancy_years(result.get("life_expectancy"))
    return result


def list_countries() -> list[dict[str, Any]]:
    cache = load_cache()
    countries = cache.get("countries", {})
    items: list[dict[str, Any]] = []
    for code, info in countries.items():
        if not isinstance(info, dict):
            continue
        name = info.get("name") or code
        region = info.get("region")
        if region is not None and not isinstance(region, str):
            region = str(region)
        items.append(
            {
                "code": code,
                "name": str(name),
                "life_expectancy": _safe_life_expectancy_years(info.get("life_expectancy")),
                "region": region,
            }
        )
    return sorted(items, key=lambda c: c["name"].casefold())


def merge_country(code: str, payload: dict[str, Any]) -> None:
    cache = load_cache()
    countries = cache.setdefault("countries", {})
    existing = countries.get(code.upper(), {})
    existing.update(payload)
    existing["code"] = code.upper()
    if existing.get("life_expectancy") is not None:
        existing["life_expectancy"] = _safe_life_expectancy_years(existing["life_expectancy"])
    countries[code.upper()] = existing
    cache["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_cache(cache)
