"""Market list, detail, and risk endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.db import fetch_one, fetch_records

router = APIRouter()


@router.get("")
def list_markets(
    chain: str | None = Query(None, description="Filter by chain (ethereum, base, arbitrum)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    params: dict = {"limit": limit, "offset": offset}
    chain_filter = ""
    if chain:
        chain_filter = "WHERE chain = :chain"
        params["chain"] = chain.lower()

    return fetch_records(
        f"""
        SELECT
            market_id,
            chain,
            loan_symbol,
            total_supply_volume,
            total_borrow_volume,
            total_supply_volume_usd,
            total_borrow_volume_usd,
            outstanding_borrow,
            outstanding_borrow_usd,
            net_liquidity_flow_usd
        FROM fact_market_activity
        {chain_filter}
        ORDER BY total_supply_volume_usd DESC NULLS LAST
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


@router.get("/{market_id}")
def get_market(
    market_id: str,
    chain: str | None = Query(None, description="Disambiguate when querying a specific chain"),
) -> dict:
    params: dict = {"market_id": market_id.lower()}
    chain_filter = ""
    if chain:
        chain_filter = "AND chain = :chain"
        params["chain"] = chain.lower()

    activity = fetch_one(
        f"""
        SELECT *
        FROM fact_market_activity
        WHERE LOWER(market_id) = :market_id
        {chain_filter}
        LIMIT 1
        """,
        params,
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Market not found")

    market_chain = activity["chain"]
    lookup_params = {"market_id": market_id.lower(), "chain": market_chain}

    credit = fetch_one(
        """
        SELECT *
        FROM fact_credit_risk
        WHERE LOWER(market_id) = :market_id AND chain = :chain
        LIMIT 1
        """,
        lookup_params,
    )
    liquidity = fetch_one(
        """
        SELECT *
        FROM fact_liquidity_risk
        WHERE LOWER(market_id) = :market_id AND chain = :chain
        LIMIT 1
        """,
        lookup_params,
    )
    concentration = fetch_one(
        """
        SELECT *
        FROM fact_concentration_risk
        WHERE LOWER(market_id) = :market_id AND chain = :chain
        LIMIT 1
        """,
        lookup_params,
    )
    dimension = fetch_one(
        """
        SELECT *
        FROM dim_market
        WHERE LOWER(market_id) = :market_id AND chain = :chain
        LIMIT 1
        """,
        lookup_params,
    )

    return {
        "activity": activity,
        "dimension": dimension,
        "credit_risk": credit,
        "liquidity_risk": liquidity,
        "concentration_risk": concentration,
    }
