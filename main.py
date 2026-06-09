import argparse
import os

import pandas as pd

from extractors.borrow import fetch_borrow_events, transform_borrow_events
from extractors.repay import fetch_repay_events, transform_repay_events
from extractors.supply import fetch_supply_events, transform_supply_events
from extractors.withdraw import fetch_withdraw_events, transform_withdraw_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrate event extraction.")
    parser.add_argument("--chain", default="ethereum")
    parser.add_argument("--from-block", type=int, required=True)
    parser.add_argument("--to-block", type=int, required=True)
    parser.add_argument("--event", choices=["supply", "borrow", "repay", "withdraw", "all"], default="supply", help="Which extractor to run")
    parser.add_argument("--output", default=None, help="Output CSV path (single event) or directory (when running --event all)")

    args = parser.parse_args()

    # Helper to determine default output for a single extractor
    def default_output_for(event_name: str) -> str:
        return f"data/{event_name}_events.csv"

    # Run and write for a single extractor
    def run_and_write(event_name: str, raw_events_fn, transform_fn, out_path: str | None):
        raw = raw_events_fn(
            chain_name=args.chain,
            from_block=args.from_block,
            to_block=args.to_block,
        )
        rows = transform_fn(raw, chain_name=args.chain)
        df = pd.DataFrame(rows)

        out = out_path or default_output_for(event_name)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Wrote {len(df)} rows to {out}")

    if args.event == "all":
        # If --output provided and is a directory, use it; otherwise default per-extractor
        out_dir = None
        if args.output:
            # treat provided output as directory if it does not end with .csv
            if args.output.endswith(".csv"):
                out_dir = os.path.dirname(args.output) or "."
            else:
                out_dir = args.output

        # supply
        supply_out = os.path.join(out_dir, "supply_events.csv") if out_dir else default_output_for("supply")
        run_and_write("supply", fetch_supply_events, transform_supply_events, supply_out)

        # borrow
        borrow_out = os.path.join(out_dir, "borrow_events.csv") if out_dir else default_output_for("borrow")
        run_and_write("borrow", fetch_borrow_events, transform_borrow_events, borrow_out)

        # repay
        repay_out = os.path.join(out_dir, "repay_events.csv") if out_dir else default_output_for("repay")
        run_and_write("repay", fetch_repay_events, transform_repay_events, repay_out)

        # withdraw
        withdraw_out = os.path.join(out_dir, "withdraw_events.csv") if out_dir else default_output_for("withdraw")
        run_and_write("withdraw", fetch_withdraw_events, transform_withdraw_events, withdraw_out)
    else:
        # single event
        if args.event == "supply":
            run_and_write("supply", fetch_supply_events, transform_supply_events, args.output)
        elif args.event == "borrow":
            run_and_write("borrow", fetch_borrow_events, transform_borrow_events, args.output)
        elif args.event == "repay":
            run_and_write("repay", fetch_repay_events, transform_repay_events, args.output)
        elif args.event == "withdraw":
            run_and_write("withdraw", fetch_withdraw_events, transform_withdraw_events, args.output)


if __name__ == "__main__":
    main()
