# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from typing import Any

from contract_loader import get_contract
from config import CHAINS


def normalize_market_id(market_id: Any) -> str:
    if hasattr(market_id, "hex") and not isinstance(market_id, str):
        market_id = market_id.hex()
    if isinstance(market_id, str) and not market_id.startswith("0x"):
        market_id = f"0x{market_id}"
    return market_id


def resolve_market(chain_name: str, market_id: Any) -> dict[str, Any]:
    if chain_name not in CHAINS:
        raise ValueError(f"Unknown chain: {chain_name}")
    market_id = normalize_market_id(market_id)
    w3, contract = get_contract(chain_name)
    params = contract.functions.idToMarketParams(market_id).call()
    return {
        "chain": chain_name,
        "market_id": market_id,
        "loan_token": params[0],
        "collateral_token": params[1],
        "oracle": params[2],
        "irm": params[3],
        "lltv": params[4],
    }


def extract_market_ids(event_rows: list[dict[str, Any]]) -> list[str]:
    market_ids: set[str] = set()
    for row in event_rows:
        market_id = row.get("market_id")
        if market_id is not None:
            market_ids.add(normalize_market_id(market_id))
    return sorted(market_ids)


def resolve_markets(chain_name: str, market_ids: list[Any]) -> list[dict[str, Any]]:
    return [resolve_market(chain_name, market_id) for market_id in market_ids]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resolve Morpho market IDs and show results.")
    parser.add_argument(
        "--chains",
        nargs="+",
        default=list(CHAINS.keys()),
        help=f"Chains to resolve (default: all). Available: {list(CHAINS.keys())}",
    )
    parser.add_argument(
        "--market-ids",
        nargs="+",
        required=True,
        help="Market IDs to resolve (hex strings, e.g. 0x123...)",
    )
    args = parser.parse_args()

    for chain in args.chains:
        if chain not in CHAINS:
            print(f"⚠️  Chain {chain} not found in config. Skipping.")
            continue

        print(f"\n📍 Resolving markets for {chain}...")
        try:
            markets = resolve_markets(chain, args.market_ids)
            print(f"✅ Resolved {len(markets)} markets on {chain}")
            if markets:
                print(markets[0])
        except Exception as e:
            print(f"❌ Error resolving markets on {chain}: {e}")