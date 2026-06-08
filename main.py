import argparse
import os

import pandas as pd

from extractors.supply import fetch_supply_events, transform_supply_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate supply event extraction.")
    parser.add_argument("--chain", default="ethereum")
    parser.add_argument("--from-block", type=int, required=True)
    parser.add_argument("--to-block", type=int, required=True)
    parser.add_argument("--output", default="data/supply_events.csv")

    args = parser.parse_args()

    raw_events = fetch_supply_events(
        chain_name=args.chain,
        from_block=args.from_block,
        to_block=args.to_block,
    )

    rows = transform_supply_events(raw_events, chain_name=args.chain)
    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
