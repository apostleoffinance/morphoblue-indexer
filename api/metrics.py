"""Chart and leaderboard endpoints for frontend dashboards."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.db import fetch_records

router = APIRouter()


@router.get("/supply-by-asset")
def supply_by_asset() -> list[dict]:
    return fetch_records(
        """
        SELECT loan_symbol, total_supply, total_supply_usd
        FROM mart_supply_activity
        ORDER BY total_supply_usd DESC NULLS LAST
        """
    )


@router.get("/borrow-by-asset")
def borrow_by_asset() -> list[dict]:
    return fetch_records(
        """
        SELECT loan_symbol, total_borrow, total_borrow_usd
        FROM mart_borrow_activity
        ORDER BY total_borrow_usd DESC NULLS LAST
        """
    )


@router.get("/top-suppliers")
def top_suppliers(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    return fetch_records(
        """
        SELECT supplier, supplied, supplied_usd
        FROM mart_supplier_totals
        ORDER BY supplied DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )


@router.get("/top-borrowers")
def top_borrowers(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    return fetch_records(
        """
        SELECT borrower, borrowed, borrowed_usd
        FROM mart_borrower_totals
        ORDER BY borrowed DESC NULLS LAST
        LIMIT :limit
        """,
        {"limit": limit},
    )
