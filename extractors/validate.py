import os
from dataclasses import dataclass, field

import pandas as pd

EVENT_NAMES = ("supply", "borrow", "repay", "withdraw")


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.info.append(message)


def _filter_chain(df: pd.DataFrame, chain: str | None) -> pd.DataFrame:
    if chain and "chain" in df.columns:
        return df[df["chain"] == chain]
    return df


def _event_paths(data_dir: str) -> dict[str, str]:
    return {name: f"{data_dir}/{name}_events.csv" for name in EVENT_NAMES}


def _enriched_path(data_dir: str, event_name: str) -> str:
    return f"{data_dir}/{event_name}_events_enriched.csv"


def validate_block_range(
    df: pd.DataFrame,
    event_name: str,
    from_block: int | None,
    to_block: int | None,
    result: ValidationResult,
) -> None:
    if df.empty:
        result.add_info(f"{event_name}: no rows")
        return

    min_block = int(df["block_number"].min())
    max_block = int(df["block_number"].max())
    result.add_info(f"{event_name}: rows={len(df)}, blocks={min_block}-{max_block}")

    if from_block is not None and min_block < from_block:
        result.add_error(
            f"{event_name}: min block {min_block} is below --from-block {from_block}"
        )
    if to_block is not None and max_block > to_block:
        result.add_error(
            f"{event_name}: max block {max_block} is above --to-block {to_block}"
        )


def validate_enriched_matches_base(
    event_name: str,
    base_df: pd.DataFrame,
    enriched_df: pd.DataFrame,
    result: ValidationResult,
) -> None:
    if len(base_df) != len(enriched_df):
        result.add_error(
            f"{event_name}: enriched row count {len(enriched_df)} "
            f"does not match base row count {len(base_df)}"
        )
        return

    if base_df.empty:
        result.add_info(f"{event_name}: enriched matches base (0 rows)")
        return

    if not base_df["transaction_hash"].equals(enriched_df["transaction_hash"]):
        result.add_error(f"{event_name}: transaction_hash values do not match enriched file")
        return

    result.add_info(f"{event_name}: enriched matches base ({len(base_df)} rows)")


def validate_market_coverage(
    event_name: str,
    event_df: pd.DataFrame,
    market_ids: set[str],
    result: ValidationResult,
) -> None:
    if event_df.empty:
        return

    missing = set(event_df["market_id"].dropna().astype(str)) - market_ids
    if missing:
        sample = sorted(missing)[:5]
        result.add_error(
            f"{event_name}: {len(missing)} market_id(s) missing from market_lookup "
            f"(e.g. {sample})"
        )
    else:
        result.add_info(
            f"{event_name}: all {event_df['market_id'].nunique()} market_id(s) found in market_lookup"
        )


def validate_enrichment_quality(
    event_name: str,
    enriched_df: pd.DataFrame,
    result: ValidationResult,
) -> None:
    if enriched_df.empty or "loan_symbol" not in enriched_df.columns:
        return

    blank = enriched_df["loan_symbol"].isna() | (enriched_df["loan_symbol"] == "")
    blank_count = int(blank.sum())
    if blank_count:
        result.add_warning(
            f"{event_name}: {blank_count} enriched row(s) have blank loan_symbol "
            "(market or token lookup may be stale)"
        )


def _chains_to_validate(
    chains: list[str] | None,
    data_dir: str,
) -> list[str | None]:
    if not chains:
        return [None]

    paths = _event_paths(data_dir)
    present: set[str] = set()
    for path in paths.values():
        if os.path.exists(path):
            df = pd.read_csv(path)
            if "chain" in df.columns:
                present.update(df["chain"].dropna().astype(str).unique())

    return [chain for chain in chains if chain in present or not present]


def run_validations(
    data_dir: str,
    from_block: int | None = None,
    to_block: int | None = None,
    chain: str | None = None,
    chains: list[str] | None = None,
    block_ranges: dict[str, tuple[int, int]] | None = None,
) -> ValidationResult:
    result = ValidationResult()
    paths = _event_paths(data_dir)
    market_path = f"{data_dir}/market_lookup.csv"
    chains_to_check = chains if chains else ([chain] if chain else [None])

    if not chains_to_check or chains_to_check == [None]:
        chains_to_check = _chains_to_validate(None, data_dir)

    found_event_files = 0
    for chain_name in chains_to_check:
        label = chain_name or "all"
        if chain_name:
            result.add_info(f"--- {chain_name} ---")

        market_ids: set[str] = set()
        if os.path.exists(market_path):
            markets_df = _filter_chain(pd.read_csv(market_path), chain_name)
            market_ids = set(markets_df["market_id"].dropna().astype(str))
            result.add_info(f"{label}: market_lookup has {len(market_ids)} unique market_id(s)")
        else:
            result.add_warning(f"{label}: market_lookup not found at {market_path}")

        chain_from = from_block
        chain_to = to_block
        if chain_name and block_ranges and chain_name in block_ranges:
            chain_from, chain_to = block_ranges[chain_name]

        for event_name, path in paths.items():
            if not os.path.exists(path):
                if chain_name == chains_to_check[0]:
                    result.add_warning(f"{event_name}: missing {path}")
                continue

            if chain_name == chains_to_check[0]:
                found_event_files += 1

            base_df = _filter_chain(pd.read_csv(path), chain_name)
            prefix = f"{label}/{event_name}" if chain_name else event_name
            validate_block_range(base_df, prefix, chain_from, chain_to, result)

            if market_ids:
                validate_market_coverage(prefix, base_df, market_ids, result)

            enriched_path = _enriched_path(data_dir, event_name)
            if not os.path.exists(enriched_path):
                if chain_name:
                    result.add_warning(f"{prefix}: missing enriched file {enriched_path}")
                continue

            enriched_df = _filter_chain(pd.read_csv(enriched_path), chain_name)
            validate_enriched_matches_base(prefix, base_df, enriched_df, result)
            validate_enrichment_quality(prefix, enriched_df, result)

    if found_event_files == 0:
        result.add_error(f"no event CSV files found in {data_dir}")

    return result


def print_validation_report(result: ValidationResult) -> None:
    for line in result.info:
        print(f"  [ok]   {line}")
    for line in result.warnings:
        print(f"  [warn] {line}")
    for line in result.errors:
        print(f"  [fail] {line}")

    if result.ok:
        print("Validation passed.")
    else:
        print(f"Validation failed with {len(result.errors)} error(s).")
