from decimal import Decimal, InvalidOperation
from typing import Any

from extractors.token_lookup import normalize_token_address


def normalize_amount(raw_amount: Any, decimals: Any) -> float | None:
    if raw_amount is None or decimals is None:
        return None
    try:
        amount = Decimal(str(raw_amount))
        divisor = Decimal(10) ** int(decimals)
        return float(amount / divisor)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None


def _market_key(chain: Any, market_id: Any) -> tuple[str, str] | None:
    if chain is None or market_id is None:
        return None
    return (str(chain), str(market_id))


def _token_key(chain: Any, token_address: Any) -> tuple[str, str] | None:
    if chain is None or token_address is None:
        return None
    return (str(chain), normalize_token_address(token_address))


def _index_markets(market_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in market_rows:
        key = _market_key(row.get("chain"), row.get("market_id"))
        if key:
            indexed[key] = row
    return indexed


def _index_tokens(token_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in token_rows:
        key = _token_key(row.get("chain"), row.get("token_address"))
        if key:
            indexed[key] = row
    return indexed


def _index_prices(price_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in price_rows:
        key = _token_key(row.get("chain"), row.get("token_address"))
        if key:
            indexed[key] = row
    return indexed


def enrich_event_row(
    event: dict[str, Any],
    markets_by_key: dict[tuple[str, str], dict[str, Any]],
    tokens_by_key: dict[tuple[str, str], dict[str, Any]],
    prices_by_key: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    row = dict(event)
    market = markets_by_key.get(_market_key(row.get("chain"), row.get("market_id")))
    if not market:
        row.update(
            {
                "loan_token": None,
                "collateral_token": None,
                "loan_symbol": None,
                "collateral_symbol": None,
                "loan_decimals": None,
                "normalized_assets": None,
                "price_usd": None,
                "amount_usd": None,
            }
        )
        return row

    loan_token = normalize_token_address(market["loan_token"])
    collateral_token = normalize_token_address(market["collateral_token"])
    chain = row.get("chain")
    loan = tokens_by_key.get(_token_key(chain, loan_token), {})
    collateral = tokens_by_key.get(_token_key(chain, collateral_token), {})
    price_row = prices_by_key.get(_token_key(chain, loan_token), {})

    loan_decimals = loan.get("decimals")
    normalized = normalize_amount(row.get("assets"), loan_decimals)
    price_usd = price_row.get("price_usd")
    amount_usd = None
    if normalized is not None and price_usd is not None:
        amount_usd = float(normalized) * float(price_usd)

    row.update(
        {
            "loan_token": loan_token,
            "collateral_token": collateral_token,
            "loan_symbol": loan.get("symbol"),
            "collateral_symbol": collateral.get("symbol"),
            "loan_decimals": loan_decimals,
            "normalized_assets": normalized,
            "price_usd": price_usd,
            "amount_usd": amount_usd,
        }
    )
    return row


def enrich_events(
    event_rows: list[dict[str, Any]],
    market_rows: list[dict[str, Any]],
    token_rows: list[dict[str, Any]],
    price_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    markets_by_key = _index_markets(market_rows)
    tokens_by_key = _index_tokens(token_rows)
    prices_by_key = _index_prices(price_rows or [])
    return [
        enrich_event_row(event, markets_by_key, tokens_by_key, prices_by_key)
        for event in event_rows
    ]
