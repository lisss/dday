#!/usr/bin/env python3
"""Generate data/countries_seed.json from World Bank public APIs."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "countries_seed.json"

WORLD_BANK_BASE = "https://api.worldbank.org/v2/country"

WB_INDICATORS = {
    "life_expectancy": "SP.DYN.LE00.IN",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "school_enrollment": "SE.SEC.ENRR",
}


def _get_json(url: str, params: dict | None = None) -> object:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "dday-seed-generator/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_wb_countries() -> list[dict]:
    payload = _get_json(WORLD_BANK_BASE, {"format": "json", "per_page": "400"})
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    rows = payload[1]
    countries: list[dict] = []
    for row in rows:
        code = row.get("iso2Code")
        if not code or len(code) != 2 or not row.get("capitalCity"):
            continue
        region = (row.get("region") or {}).get("value", "").strip() or None
        countries.append(
            {
                "code": code.upper(),
                "name": row.get("name", code),
                "region": region,
                "subregion": (row.get("adminregion") or {}).get("value") or None,
                "capital": row.get("capitalCity"),
                "population": None,
                "languages": [],
                "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None,
            }
        )
    return countries


def fetch_wb_indicator(country_code: str, indicator: str) -> float | None:
    url = f"{WORLD_BANK_BASE}/{country_code}/indicator/{indicator}"
    try:
        payload = _get_json(url, {"format": "json", "per_page": "5", "date": "2018:2024"})
        if not isinstance(payload, list) or len(payload) < 2:
            return None
        for row in payload[1]:
            value = row.get("value")
            if value is not None:
                return float(value)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return None


def enrich_country(entry: dict) -> dict:
    code = entry["code"]
    entry["life_expectancy"] = fetch_wb_indicator(code, WB_INDICATORS["life_expectancy"])
    entry["gdp_per_capita_usd"] = fetch_wb_indicator(code, WB_INDICATORS["gdp_per_capita"])
    entry["school_enrollment_secondary_pct"] = fetch_wb_indicator(
        code, WB_INDICATORS["school_enrollment"]
    )
    entry["ethnicity"] = [
        {"group": "Mixed/Other", "share": 100.0, "note": "Detailed breakdown unavailable"}
    ]
    entry["weather_description"] = "Refresh via cron or country detail fetch"
    return entry


def main() -> None:
    entries = fetch_wb_countries()
    entries.sort(key=lambda c: c["name"])

    enriched: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(enrich_country, entry) for entry in entries]
        for future in as_completed(futures):
            enriched.append(future.result())

    enriched.sort(key=lambda c: c["name"])
    countries = {entry["code"]: entry for entry in enriched}
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "countries": countries,
    }
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SEED_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(countries)} countries to {SEED_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
