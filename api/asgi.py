"""ASGI entrypoint for Docker — API at /api, static frontend at /."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .index import app as api_app

app = FastAPI(title="Death Predictor", docs_url=None, redoc_url=None)
app.mount("/api", api_app)

static_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
