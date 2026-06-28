"""FastAPI application for death prediction API."""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import storage
from .data_fetcher import fetch_country_data, refresh_all_countries
from .predictor import (
    ACTIVITY_LABELS,
    PredictRequest,
    PredictResponse,
    predict_death,
)

app = FastAPI(
    title="Death Predictor API",
    description="Country statistics and statistical death date estimation",
    version="1.0.0",
    root_path="/api" if os.environ.get("VERCEL") else "",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "death-predictor",
        "endpoints": [
            "GET /api/health",
            "GET /api/countries",
            "GET /api/countries/{code}",
            "GET /api/activities",
            "POST /api/predict",
            "GET /api/cron/fetch-data",
        ],
    }


@app.get("/health")
async def health():
    cache = storage.load_cache()
    return {
        "status": "ok",
        "cache_updated_at": cache.get("updated_at"),
        "country_count": len(cache.get("countries", {})),
    }


@app.get("/countries")
async def countries():
    cache = storage.load_cache()
    return {"countries": storage.list_countries(), "updated_at": cache.get("updated_at")}


@app.get("/countries/{code}")
async def country_detail(code: str):
    info = storage.get_country(code)
    if not info:
        info = await fetch_country_data(code)
    if not info:
        raise HTTPException(status_code=404, detail=f"Country {code} not found")
    return info


@app.get("/activities")
async def activities():
    return {
        "activities": [
            {"type": key, "label": label}
            for key, label in ACTIVITY_LABELS.items()
        ]
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest):
    return predict_death(payload)


def _verify_cron_secret(authorization: str | None) -> None:
    secret = os.environ.get("CRON_SECRET")
    if not secret:
        return
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized cron request")


@app.get("/cron/fetch-data")
async def cron_fetch_data(authorization: str | None = Header(default=None)):
    _verify_cron_secret(authorization)
    result = await refresh_all_countries()
    return {"status": "completed", **result}
