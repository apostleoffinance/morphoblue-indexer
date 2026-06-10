from datetime import datetime, timezone
from typing import Any

from contract_loader import get_block_timestamp, get_contract
from config import CHAINS


def normalize_repay_event(event: dict[str, Any], chain_name: str) -> dict[str, Any]:
    args = dict(event.get("args") or {})
    market_id = args.get("id") or args.get("marketId")

    if hasattr(market_id, "hex"):
        market_id = market_id.hex()

    if isinstance(market_id, str) and not market_id.startswith("0x"):
        market_id = f"0x{market_id}"

    return {
        "chain": chain_name,
        "event": event.get("event"),
        "address": event.get("address"),
        "block_number": event.get("blockNumber"),
        "block_timestamp": event.get("block_timestamp"),
        "block_hash": event.get("blockHash").hex() if event.get("blockHash") is not None else None,
        "transaction_hash": event.get("transactionHash").hex() if event.get("transactionHash") is not None else None,
        "transaction_index": event.get("transactionIndex"),
        "log_index": event.get("logIndex"),
        "transaction_log_index": event.get("transactionLogIndex"),
        "repayer": args.get("onBehalf"),
        "caller": args.get("caller"),
        "assets": args.get("assets"),
        "shares": args.get("shares"),
        "market_id": market_id,
    }


def transform_repay_events(events: list[dict[str, Any]], chain_name: str = "ethereum") -> list[dict[str, Any]]:
    return [normalize_repay_event(event, chain_name) for event in events]


def fetch_repay_events(chain_name: str, from_block: int, to_block: int) -> list[dict[str, Any]]:
    if chain_name not in CHAINS:
        raise ValueError(f"Unknown chain: {chain_name}")

    w3, contract = get_contract(chain_name)
    raw_events = contract.events.Repay().get_logs(
        from_block=from_block,
        to_block=to_block,
    )

    block_cache: dict[int, int] = {}
    events_with_timestamp = []
    for raw_event in raw_events:
        event_dict = dict(raw_event)
        block_number = event_dict["blockNumber"]
        if block_number not in block_cache:
            block_cache[block_number] = get_block_timestamp(w3, block_number)
        timestamp = block_cache[block_number]
        event_dict["block_timestamp"] = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        events_with_timestamp.append(event_dict)

    return events_with_timestamp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch Repay events from Morpho Blue contracts"
    )
    parser.add_argument(
        "--chains",
        nargs="+",
        default=list(CHAINS.keys()),
        help=f"Chains to fetch from (default: all). Available: {list(CHAINS.keys())}",
    )
    parser.add_argument(
        "--from-block",
        type=int,
        required=True,
        help="Start block",
    )
    parser.add_argument(
        "--to-block",
        type=int,
        required=True,
        help="End block",
    )

    args = parser.parse_args()

    for chain_name in args.chains:
        if chain_name not in CHAINS:
            print(f"⚠️  Chain {chain_name} not found in config. Skipping.")
            continue

        print(f"\n📍 Fetching Repay events from {chain_name}...")
        try:
            raw_events = fetch_repay_events(
                chain_name=chain_name,
                from_block=args.from_block,
                to_block=args.to_block,
            )
            events = transform_repay_events(raw_events, chain_name=chain_name)
            print(f"✅ Found {len(events)} Repay events on {chain_name}")
            if events:
                print(events[0])
        except Exception as e:
            print(f"❌ Error fetching from {chain_name}: {e}")
