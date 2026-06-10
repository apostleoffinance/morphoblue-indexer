import argparse
import os

import pandas as pd

from config import CHAINS
from extractors.borrow import fetch_borrow_events, transform_borrow_events
from extractors.enrich import enrich_events
from extractors.market_lookup import extract_market_ids, resolve_markets
from extractors.repay import fetch_repay_events, transform_repay_events
from extractors.supply import fetch_supply_events, transform_supply_events
from extractors.token_lookup import extract_token_addresses, resolve_tokens
from extractors.validate import print_validation_report, run_validations
from extractors.withdraw import fetch_withdraw_events, transform_withdraw_events

DEFAULT_EVENT_PATHS = [
    "data/supply_events.csv",
    "data/borrow_events.csv",
    "data/repay_events.csv",
    "data/withdraw_events.csv",
]


def parse_chains(chain_args: list[str], parser: argparse.ArgumentParser) -> list[str]:
    if len(chain_args) == 1 and chain_args[0] == "all":
        return list(CHAINS.keys())

    chains: list[str] = []
    for chain in chain_args:
        if chain not in CHAINS:
            parser.error(f"Unknown chain '{chain}'. Available: {list(CHAINS.keys())} or 'all'")
        if chain not in chains:
            chains.append(chain)
    return chains


def parse_block_ranges(
    chains: list[str],
    from_block: int | None,
    to_block: int | None,
    block_range_specs: list[str] | None,
    parser: argparse.ArgumentParser,
) -> dict[str, tuple[int, int]]:
    ranges: dict[str, tuple[int, int]] = {}

    for spec in block_range_specs or []:
        if ":" not in spec or "-" not in spec.split(":", 1)[1]:
            parser.error(f"Invalid --block-range '{spec}'. Expected CHAIN:FROM-TO")
        chain_part, blocks = spec.split(":", 1)
        from_part, to_part = blocks.split("-", 1)
        chain_name = chain_part.strip()
        if chain_name not in CHAINS:
            parser.error(f"Unknown chain in --block-range: {chain_name}")
        ranges[chain_name] = (int(from_part), int(to_part))

    for chain in chains:
        if chain not in ranges:
            if from_block is None or to_block is None:
                parser.error(
                    f"--from-block and --to-block are required for '{chain}' "
                    "(or pass --block-range {chain}:FROM-TO)"
                )
            ranges[chain] = (from_block, to_block)

    return ranges


def default_output_for(event_name: str, data_dir: str = "data") -> str:
    return os.path.join(data_dir, f"{event_name}_events.csv")


def default_enriched_output(path: str) -> str:
    if path.endswith("_events.csv"):
        return path.replace("_events.csv", "_events_enriched.csv")
    base, ext = os.path.splitext(path)
    return f"{base}_enriched{ext}"


def data_dir_from_output(output: str | None) -> str:
    if not output:
        return "data"
    if output.endswith(".csv"):
        return os.path.dirname(output) or "."
    return output


def merge_csv(new_df: pd.DataFrame, path: str, chains_updated: list[str]) -> pd.DataFrame:
    if not chains_updated or "chain" not in new_df.columns or not os.path.exists(path):
        return new_df

    existing = pd.read_csv(path)
    if "chain" not in existing.columns:
        return new_df

    kept = existing[~existing["chain"].isin(chains_updated)]
    return pd.concat([kept, new_df], ignore_index=True)


def write_csv(df: pd.DataFrame, path: str, chains_updated: list[str] | None = None) -> None:
    if chains_updated:
        df = merge_csv(df, path, chains_updated)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")


def collect_market_ids(event_paths: list[str], chain: str | None = None) -> list[str]:
    all_ids: set[str] = set()
    for path in event_paths:
        if not os.path.exists(path):
            continue
        events_df = pd.read_csv(path)
        if chain and "chain" in events_df.columns:
            events_df = events_df[events_df["chain"] == chain]
        all_ids.update(extract_market_ids(events_df.to_dict("records")))
    return sorted(all_ids)


def run_and_write_events(
    event_name: str,
    raw_events_fn,
    transform_fn,
    chains: list[str],
    block_ranges: dict[str, tuple[int, int]],
    out_path: str,
) -> None:
    frames: list[pd.DataFrame] = []
    for chain in chains:
        from_block, to_block = block_ranges[chain]
        print(f"Fetching {event_name} on {chain} (blocks {from_block}-{to_block})...")
        raw = raw_events_fn(chain_name=chain, from_block=from_block, to_block=to_block)
        rows = transform_fn(raw, chain_name=chain)
        if rows:
            frames.append(pd.DataFrame(rows))
        else:
            print(f"  No {event_name} events on {chain}")

    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame()
    write_csv(df, out_path, chains_updated=chains)


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate event extraction.")
    parser.add_argument(
        "--chain",
        nargs="+",
        default=["ethereum"],
        metavar="CHAIN",
        help="One or more chains (ethereum base arbitrum) or 'all'",
    )
    parser.add_argument("--from-block", type=int, help="Block range start (all chains unless --block-range is set)")
    parser.add_argument("--to-block", type=int, help="Block range end (all chains unless --block-range is set)")
    parser.add_argument(
        "--block-range",
        action="append",
        metavar="CHAIN:FROM-TO",
        help="Per-chain block range, e.g. ethereum:22800000-22801000",
    )
    parser.add_argument(
        "--event",
        choices=["supply", "borrow", "repay", "withdraw", "market", "token", "enrich", "validate", "all"],
        default="supply",
        help="Which extractor to run",
    )
    parser.add_argument("--input", default=None, help="Input CSV path for market/token/enrich steps")
    parser.add_argument("--output", default=None, help="Output CSV path (single event) or directory (when running --event all)")

    args = parser.parse_args()
    chains = parse_chains(args.chain, parser)
    data_dir = data_dir_from_output(args.output)

    needs_blocks = args.event not in {"market", "token", "enrich", "validate"}
    block_ranges: dict[str, tuple[int, int]] = {}
    if args.block_range:
        block_ranges = parse_block_ranges(
            chains, args.from_block, args.to_block, args.block_range, parser
        )
    elif needs_blocks:
        block_ranges = parse_block_ranges(
            chains, args.from_block, args.to_block, None, parser
        )
        if len(chains) > 1:
            print(
                f"Using the same block range {args.from_block}-{args.to_block} for: "
                + ", ".join(chains)
            )
    elif args.from_block is not None and args.to_block is not None:
        block_ranges = {chain: (args.from_block, args.to_block) for chain in chains}

    event_extractors = {
        "supply": (fetch_supply_events, transform_supply_events),
        "borrow": (fetch_borrow_events, transform_borrow_events),
        "repay": (fetch_repay_events, transform_repay_events),
        "withdraw": (fetch_withdraw_events, transform_withdraw_events),
    }

    if args.event == "all":
        out_dir = data_dir if args.output and not args.output.endswith(".csv") else None
        for event_name, (fetch_fn, transform_fn) in event_extractors.items():
            out_path = (
                os.path.join(out_dir, f"{event_name}_events.csv")
                if out_dir
                else default_output_for(event_name, data_dir)
            )
            run_and_write_events(
                event_name, fetch_fn, transform_fn, chains, block_ranges, out_path
            )

    elif args.event in event_extractors:
        fetch_fn, transform_fn = event_extractors[args.event]
        out_path = args.output or default_output_for(args.event, data_dir)
        run_and_write_events(
            args.event, fetch_fn, transform_fn, chains, block_ranges, out_path
        )

    elif args.event == "market":
        if args.input:
            event_paths = [p.strip() for p in args.input.split(",")]
        else:
            event_paths = [os.path.join(data_dir, os.path.basename(p)) for p in DEFAULT_EVENT_PATHS]

        all_rows: list[dict] = []
        for chain in chains:
            market_ids = collect_market_ids(event_paths, chain)
            if not market_ids:
                print(f"No market_ids found for {chain}, skipping")
                continue
            print(f"Resolving {len(market_ids)} market(s) on {chain}...")
            all_rows.extend(resolve_markets(chain, market_ids))

        df = pd.DataFrame(all_rows)
        out = args.output or os.path.join(data_dir, "market_lookup.csv")
        write_csv(df, out, chains_updated=chains)

    elif args.event == "token":
        token_input = args.input or os.path.join(data_dir, "market_lookup.csv")
        market_df = pd.read_csv(token_input)

        all_rows: list[dict] = []
        for chain in chains:
            chain_markets = market_df
            if "chain" in market_df.columns:
                chain_markets = market_df[market_df["chain"] == chain]
            token_addresses = extract_token_addresses(chain_markets.to_dict("records"))
            if not token_addresses:
                print(f"No tokens found for {chain}, skipping")
                continue
            print(f"Resolving {len(token_addresses)} token(s) on {chain}...")
            all_rows.extend(resolve_tokens(chain, token_addresses))

        df = pd.DataFrame(all_rows)
        if "decimals" in df.columns:
            df["decimals"] = df["decimals"].astype("Int64")

        out = args.output or os.path.join(data_dir, "token_lookup.csv")
        write_csv(df, out, chains_updated=chains)

    elif args.event == "enrich":
        if not args.input:
            parser.error("--input is required for --event enrich (e.g. data/supply_events.csv)")

        events_df = pd.read_csv(args.input)
        markets_path = os.path.join(data_dir, "market_lookup.csv")
        tokens_path = os.path.join(data_dir, "token_lookup.csv")
        markets_df = pd.read_csv(markets_path)
        tokens_df = pd.read_csv(tokens_path)
        if "decimals" in tokens_df.columns:
            tokens_df["decimals"] = tokens_df["decimals"].astype("Int64")

        rows = enrich_events(
            events_df.to_dict("records"),
            markets_df.to_dict("records"),
            tokens_df.to_dict("records"),
        )
        df = pd.DataFrame(rows)
        if "loan_decimals" in df.columns:
            df["loan_decimals"] = df["loan_decimals"].astype("Int64")

        chains_updated = (
            events_df["chain"].dropna().astype(str).unique().tolist()
            if "chain" in events_df.columns
            else []
        )
        out = args.output or default_enriched_output(args.input)
        write_csv(df, out, chains_updated=chains_updated)

    elif args.event == "validate":
        result = run_validations(
            data_dir=data_dir,
            from_block=args.from_block,
            to_block=args.to_block,
            chains=chains,
            block_ranges=block_ranges or None,
        )
        print_validation_report(result)
        if not result.ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
