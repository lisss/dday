"""Fetch country statistics from public APIs."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from . import storage

WORLD_BANK_BASE = "https://api.worldbank.org/v2/country"
REST_COUNTRIES_BASE = "https://restcountries.com/v3.1/alpha"
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"

WB_INDICATORS = {
    "life_expectancy": "SP.DYN.LE00.IN",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "school_enrollment": "SE.SEC.ENRR",
}

ETHNICITY_BY_COUNTRY: dict[str, list[dict[str, str | float]]] = {
    "US": [
        {"group": "White", "share": 59.3},
        {"group": "Hispanic/Latino", "share": 19.1},
        {"group": "Black/African American", "share": 13.6},
        {"group": "Asian", "share": 6.3},
        {"group": "Other/Mixed", "share": 1.7},
    ],
    "GB": [
        {"group": "White", "share": 81.7},
        {"group": "Asian", "share": 9.3},
        {"group": "Black", "share": 4.0},
        {"group": "Mixed", "share": 3.0},
        {"group": "Other", "share": 2.0},
    ],
    "DE": [
        {"group": "German/European", "share": 87.0},
        {"group": "Turkish/Middle Eastern", "share": 5.0},
        {"group": "Other European", "share": 4.0},
        {"group": "Asian/African", "share": 4.0},
    ],
    "FR": [
        {"group": "French/European", "share": 85.0},
        {"group": "North African", "share": 7.0},
        {"group": "Sub-Saharan African", "share": 4.0},
        {"group": "Asian", "share": 4.0},
    ],
    "JP": [
        {"group": "Japanese", "share": 97.5},
        {"group": "Korean/Chinese/Other", "share": 2.5},
    ],
    "CN": [
        {"group": "Han Chinese", "share": 91.1},
        {"group": "Zhuang", "share": 1.3},
        {"group": "Hui", "share": 0.8},
        {"group": "Other ethnic minorities", "share": 6.8},
    ],
    "IN": [
        {"group": "Indo-Aryan", "share": 72.0},
        {"group": "Dravidian", "share": 25.0},
        {"group": "Other", "share": 3.0},
    ],
    "BR": [
        {"group": "White", "share": 45.0},
        {"group": "Mixed (Pardo)", "share": 43.0},
        {"group": "Black", "share": 10.0},
        {"group": "Asian/Indigenous", "share": 2.0},
    ],
    "NG": [
        {"group": "Hausa-Fulani", "share": 29.0},
        {"group": "Yoruba", "share": 21.0},
        {"group": "Igbo", "share": 18.0},
        {"group": "Other", "share": 32.0},
    ],
    "AU": [
        {"group": "European", "share": 72.0},
        {"group": "Asian", "share": 10.0},
        {"group": "Indigenous", "share": 3.3},
        {"group": "Other/Mixed", "share": 14.7},
    ],
}


def all_country_codes() -> list[str]:
    cache = storage.load_cache()
    return sorted(cache.get("countries", {}).keys())


async def _fetch_wb_indicator(
    client: httpx.AsyncClient, country_code: str, indicator: str
) -> float | None:
    url = f"{WORLD_BANK_BASE}/{country_code}/indicator/{indicator}"
    params = {"format": "json", "per_page": 5, "date": "2018:2024"}
    try:
        resp = await client.get(url, params=params, timeout=20.0)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2:
            return None
        for row in payload[1]:
            value = row.get("value")
            if value is not None:
                return float(value)
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    return None


async def _fetch_wb_country_meta(
    client: httpx.AsyncClient, country_code: str
) -> dict[str, Any]:
    url = f"{WORLD_BANK_BASE}/{country_code}"
    params = {"format": "json"}
    try:
        resp = await client.get(url, params=params, timeout=20.0)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list) and len(payload) > 1 and payload[1]:
            row = payload[1][0]
            lat = row.get("latitude")
            lon = row.get("longitude")
            return {
                "name": row.get("name", country_code),
                "region": (row.get("region") or {}).get("value"),
                "subregion": (row.get("adminregion") or {}).get("value"),
                "capital": row.get("capitalCity"),
                "latlng": [float(lat), float(lon)] if lat and lon else [None, None],
            }
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    return {}


async def _fetch_rest_country(
    client: httpx.AsyncClient, country_code: str
) -> dict[str, Any]:
    url = f"{REST_COUNTRIES_BASE}/{country_code}"
    params = {"fields": "name,cca2,region,subregion,capital,population,latlng,languages"}
    try:
        resp = await client.get(url, params=params, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("success") is False:
            return {}
        if isinstance(data, list) and data:
            return data[0]
    except httpx.HTTPError:
        pass
    return {}


async def _fetch_weather(
    client: httpx.AsyncClient, lat: float, lon: float
) -> dict[str, Any] | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
        "timezone": "auto",
    }
    try:
        resp = await client.get(OPEN_METEO_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        if not current:
            return None
        return {
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "source": "Open-Meteo",
        }
    except httpx.HTTPError:
        return None


def _weather_label(code: int | None) -> str:
    labels = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        95: "Thunderstorm",
    }
    if code is None:
        return "Unknown"
    return labels.get(code, f"Weather code {code}")


async def fetch_country_data(country_code: str) -> dict[str, Any]:
    code = country_code.upper()
    seed = storage.get_country(code) or {}

    async with httpx.AsyncClient() as client:
        rest_task = _fetch_rest_country(client, code)
        wb_meta_task = _fetch_wb_country_meta(client, code)
        life_task = _fetch_wb_indicator(client, code, WB_INDICATORS["life_expectancy"])
        gdp_task = _fetch_wb_indicator(client, code, WB_INDICATORS["gdp_per_capita"])
        edu_task = _fetch_wb_indicator(client, code, WB_INDICATORS["school_enrollment"])

        rest, wb_meta, life_exp, gdp, edu = await asyncio.gather(
            rest_task, wb_meta_task, life_task, gdp_task, edu_task
        )

        meta = wb_meta if wb_meta else rest
        latlng = meta.get("latlng") or seed.get("latlng")
        if not latlng and seed.get("latitude") is not None:
            latlng = [seed.get("latitude"), seed.get("longitude")]
        if not latlng:
            latlng = [None, None]

        weather = None
        if latlng[0] is not None and latlng[1] is not None:
            weather = await _fetch_weather(client, latlng[0], latlng[1])

    name = meta.get("name") or seed.get("name") or rest.get("name", {}).get("common", code)
    if isinstance(name, dict):
        name = name.get("common", code)

    ethnicity = ETHNICITY_BY_COUNTRY.get(
        code,
        seed.get("ethnicity")
        or [{"group": "Mixed/Other", "share": 100.0, "note": "Detailed breakdown unavailable"}],
    )

    result: dict[str, Any] = {
        "code": code,
        "name": name,
        "region": meta.get("region") or seed.get("region"),
        "subregion": meta.get("subregion") or seed.get("subregion"),
        "capital": meta.get("capital") or seed.get("capital") or (rest.get("capital") or [None])[0],
        "population": rest.get("population") or seed.get("population"),
        "languages": list((rest.get("languages") or {}).values()) or seed.get("languages", []),
        "life_expectancy": life_exp or seed.get("life_expectancy"),
        "gdp_per_capita_usd": gdp if gdp is not None else seed.get("gdp_per_capita_usd"),
        "school_enrollment_secondary_pct": edu if edu is not None else seed.get(
            "school_enrollment_secondary_pct"
        ),
        "ethnicity": ethnicity,
        "weather": weather,
        "weather_description": _weather_label(
            weather.get("weather_code") if weather else None
        ),
    }
    storage.merge_country(code, result)
    return result


async def refresh_all_countries(codes: list[str] | None = None) -> dict[str, Any]:
    targets = codes or all_country_codes()
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    batch_size = 15
    for i in range(0, len(targets), batch_size):
        batch = targets[i : i + batch_size]
        tasks = [fetch_country_data(code) for code in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for code, outcome in zip(batch, batch_results):
            if isinstance(outcome, Exception):
                errors[code] = str(outcome)
            else:
                results[code] = outcome

    cache = storage.load_cache()
    return {
        "updated_at": cache.get("updated_at"),
        "fetched": len(results),
        "total": len(targets),
        "errors": errors,
        "countries": list(results.keys()),
    }
