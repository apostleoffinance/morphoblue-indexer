"""Resolve USD prices for pipeline tokens via CoinGecko (primary) and DefiLlama (fallback)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from config import (
    COINGECKO_ONCHAIN_NETWORK,
    COINGECKO_PLATFORM,
    DEFILLAMA_CHAIN,
    GECKO_API_KEY,
)
from extractors.token_lookup import normalize_token_address

COINGECKO_PRO_BASE = "https://pro-api.coingecko.com/api/v3"
DEFILLAMA_COINS_BASE = "https://coins.llama.fi/prices/current"
BATCH_SIZE = 50
REQUEST_DELAY_SECONDS = 0.35


def _http_get_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _fetch_coingecko_simple(platform: str, addresses: list[str]) -> dict[str, float]:
    if not GECKO_API_KEY or not addresses:
        return {}

    prices: dict[str, float] = {}
    headers = {"x-cg-pro-api-key": GECKO_API_KEY}

    for batch in _chunked(addresses, BATCH_SIZE):
        params = urllib.parse.urlencode(
            {
                "contract_addresses": ",".join(batch),
                "vs_currencies": "usd",
            }
        )
        url = f"{COINGECKO_PRO_BASE}/simple/token_price/{platform}?{params}"
        try:
            data = _http_get_json(url, headers=headers)
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"  CoinGecko simple price failed for {platform}: {exc}")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        for address, payload in (data or {}).items():
            usd = payload.get("usd") if isinstance(payload, dict) else None
            if usd is not None:
                prices[normalize_token_address(address).lower()] = float(usd)

        time.sleep(REQUEST_DELAY_SECONDS)

    return prices


def _fetch_coingecko_onchain(network: str, addresses: list[str]) -> dict[str, float]:
    if not GECKO_API_KEY or not addresses:
        return {}

    prices: dict[str, float] = {}
    headers = {"x-cg-pro-api-key": GECKO_API_KEY}

    for batch in _chunked(addresses, BATCH_SIZE):
        joined = ",".join(batch)
        url = f"{COINGECKO_PRO_BASE}/onchain/simple/networks/{network}/token_price/{joined}"
        try:
            data = _http_get_json(url, headers=headers)
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"  CoinGecko onchain price failed for {network}: {exc}")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        token_prices = (data or {}).get("data", {}).get("attributes", {}).get("token_prices", {})
        for address, usd in token_prices.items():
            if usd is not None:
                prices[normalize_token_address(address).lower()] = float(usd)

        time.sleep(REQUEST_DELAY_SECONDS)

    return prices


def _fetch_defillama(coins: list[str]) -> dict[str, float]:
    if not coins:
        return {}

    prices: dict[str, float] = {}
    for batch in _chunked(coins, BATCH_SIZE):
        joined = ",".join(batch)
        url = f"{DEFILLAMA_COINS_BASE}/{urllib.parse.quote(joined, safe=':,')}"
        try:
            data = _http_get_json(url)
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"  DefiLlama price failed: {exc}")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        for coin_id, payload in (data or {}).get("coins", {}).items():
            if not isinstance(payload, dict):
                continue
            price = payload.get("price")
            if price is None:
                continue
            _, address = coin_id.split(":", 1)
            prices[normalize_token_address(address).lower()] = float(price)

        time.sleep(REQUEST_DELAY_SECONDS)

    return prices


def _resolve_chain_prices(chain: str, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    platform = COINGECKO_PLATFORM.get(chain)
    onchain_network = COINGECKO_ONCHAIN_NETWORK.get(chain)
    llama_chain = DEFILLAMA_CHAIN.get(chain)

    if not llama_chain:
        print(f"  Unknown chain for pricing: {chain}, skipping")
        return []

    addresses = [normalize_token_address(t["token_address"]) for t in tokens]
    lower_addresses = [a.lower() for a in addresses]
    symbol_by_address = {
        normalize_token_address(t["token_address"]).lower(): t.get("symbol")
        for t in tokens
    }

    resolved: dict[str, tuple[float, str]] = {}

    if GECKO_API_KEY and platform:
        simple_prices = _fetch_coingecko_simple(platform, lower_addresses)
        for address, price in simple_prices.items():
            resolved[address] = (price, "coingecko")

        missing = [addr for addr in lower_addresses if addr not in resolved]
        if missing and onchain_network:
            onchain_prices = _fetch_coingecko_onchain(onchain_network, missing)
            for address, price in onchain_prices.items():
                resolved[address] = (price, "coingecko_onchain")
    elif not GECKO_API_KEY:
        print("  GECKO_API_KEY not set — skipping CoinGecko, using DefiLlama only")

    missing = [addr for addr in lower_addresses if addr not in resolved]
    if missing:
        llama_coins = [f"{llama_chain}:{addr}" for addr in missing]
        llama_prices = _fetch_defillama(llama_coins)
        for address, price in llama_prices.items():
            resolved[address] = (price, "defillama")

    priced_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for address in lower_addresses:
        price_info = resolved.get(address)
        if price_info:
            price_usd, source = price_info
        else:
            price_usd, source = None, None
            print(f"  No USD price for {chain}:{address}")

        rows.append(
            {
                "chain": chain,
                "token_address": normalize_token_address(address),
                "symbol": symbol_by_address.get(address),
                "price_usd": price_usd,
                "price_source": source,
                "priced_at": priced_at,
            }
        )

    return rows


def resolve_token_prices(
    token_rows: list[dict[str, Any]],
    chains: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch USD prices for tokens in token_lookup rows."""
    chains_filter = set(chains) if chains else None
    by_chain: dict[str, list[dict[str, Any]]] = {}

    for row in token_rows:
        chain = row.get("chain")
        token_address = row.get("token_address")
        if not chain or not token_address:
            continue
        if chains_filter and chain not in chains_filter:
            continue
        by_chain.setdefault(str(chain), []).append(row)

    all_rows: list[dict[str, Any]] = []
    for chain, chain_tokens in sorted(by_chain.items()):
        unique: dict[str, dict[str, Any]] = {}
        for row in chain_tokens:
            address = normalize_token_address(row["token_address"]).lower()
            unique[address] = row
        print(f"Pricing {len(unique)} token(s) on {chain}...")
        all_rows.extend(_resolve_chain_prices(chain, list(unique.values())))

    priced = sum(1 for row in all_rows if row.get("price_usd") is not None)
    print(f"Priced {priced}/{len(all_rows)} tokens")
    return all_rows
