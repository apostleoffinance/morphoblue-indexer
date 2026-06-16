"""Shared database helpers for the analytics API."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import text

from database.connection import engine


def fetch_records(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params or {})
    return _records_from_dataframe(df)


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_records(sql, params)
    return rows[0] if rows else None


def _records_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        records.append({key: _serialize_value(value) for key, value in row.items()})
    return records


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item"):
        return _serialize_value(value.item())
    return value
