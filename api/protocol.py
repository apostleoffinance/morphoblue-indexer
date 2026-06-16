"""Protocol-level KPI endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.db import fetch_one, fetch_records

router = APIRouter()


@router.get("/summary")
def protocol_summary() -> dict:
    row = fetch_one(
        """
        SELECT
            COUNT(DISTINCT market_id) AS market_count,
            COUNT(DISTINCT chain) AS chain_count,
            COALESCE(SUM(total_supply_volume_usd), 0) AS total_supply_usd,
            COALESCE(SUM(total_borrow_volume_usd), 0) AS total_borrow_usd,
            COALESCE(SUM(total_repay_volume_usd), 0) AS total_repay_usd,
            COALESCE(SUM(total_withdraw_volume_usd), 0) AS total_withdraw_usd,
            COALESCE(SUM(outstanding_borrow_usd), 0) AS outstanding_borrow_usd,
            COALESCE(SUM(net_liquidity_flow_usd), 0) AS net_liquidity_flow_usd
        FROM fact_market_activity
        """
    )
    return row or {}


@router.get("/activity-by-chain")
def activity_by_chain() -> list[dict]:
    return fetch_records(
        """
        SELECT
            chain,
            COUNT(DISTINCT market_id) AS market_count,
            COALESCE(SUM(total_supply_volume_usd), 0) AS total_supply_usd,
            COALESCE(SUM(total_borrow_volume_usd), 0) AS total_borrow_usd,
            COALESCE(SUM(outstanding_borrow_usd), 0) AS outstanding_borrow_usd
        FROM fact_market_activity
        GROUP BY chain
        ORDER BY total_supply_usd DESC
        """
    )
