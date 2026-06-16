"""Morpho Blue Len analytics API."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.markets import router as markets_router
from api.metrics import router as metrics_router
from api.protocol import router as protocol_router

load_dotenv()

_DEFAULT_CORS = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", _DEFAULT_CORS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Morpho Blue Len API",
    description="Read-only analytics API over dbt marts in PostgreSQL.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(protocol_router, prefix="/protocol", tags=["protocol"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(markets_router, prefix="/markets", tags=["markets"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
