"""Load pipeline CSV files into PostgreSQL with correct uint256 column types."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import MetaData, inspect, text

from database.connection import engine
from database.schema import (
    NORMALIZED_COLUMNS,
    UINT256_COLUMNS,
    build_table,
    dtype_map_for_csv,
    sqlalchemy_dtypes_for_columns,
    sqlalchemy_type_for_column,
)


def _sync_table_columns(table_name: str, columns: list[str]) -> None:
    """Add any CSV columns missing from an existing Postgres table."""
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return

    existing = {col["name"] for col in inspector.get_columns(table_name)}
    missing = [col for col in columns if col not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for col in missing:
            col_type = sqlalchemy_type_for_column(col).compile(dialect=engine.dialect)
            conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {col_type}'))

DEFAULT_DATA_DIR = Path("data")

# Known enriched event tables and their CSV paths (relative to data dir).
ENRICHED_TABLES = {
    "supply_events_enriched": "supply_events_enriched.csv",
    "borrow_events_enriched": "borrow_events_enriched.csv",
    "repay_events_enriched": "repay_events_enriched.csv",
    "withdraw_events_enriched": "withdraw_events_enriched.csv",
}

DIMENSION_TABLES = {
    "market_lookup": "market_lookup.csv",
    "token_lookup": "token_lookup.csv",
    "token_prices": "token_prices.csv",
}


def read_csv_for_postgres(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    df = pd.read_csv(path, dtype=dtype_map_for_csv(header))

    for col in UINT256_COLUMNS:
        if col in df.columns:
            # Empty strings / NaN → None; preserve full integer precision as str.
            df[col] = df[col].where(df[col].notna() & (df[col].astype(str).str.strip() != ""), None)

    for col in NORMALIZED_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ("block_number", "transaction_index", "log_index", "transaction_log_index", "loan_decimals", "decimals"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df


def load_csv_to_table(csv_path: Path, table_name: str, if_exists: str = "replace") -> int:
    df = read_csv_for_postgres(csv_path)
    metadata = MetaData()
    build_table(table_name, df.columns.tolist(), metadata)
    metadata.create_all(engine, tables=[metadata.tables[table_name]])
    _sync_table_columns(table_name, df.columns.tolist())

    write_mode = if_exists
    if if_exists == "replace" and inspect(engine).has_table(table_name):
        # Truncate instead of DROP so dbt views that depend on source tables stay valid.
        with engine.begin() as conn:
            conn.execute(text(f'TRUNCATE TABLE "{table_name}"'))
        write_mode = "append"

    df.to_sql(
        table_name,
        engine,
        if_exists=write_mode,
        index=False,
        dtype=sqlalchemy_dtypes_for_columns(df.columns.tolist()),
    )
    return len(df)


def load_all(data_dir: Path = DEFAULT_DATA_DIR, if_exists: str = "replace") -> None:
    tables = {**ENRICHED_TABLES, **DIMENSION_TABLES}
    for table_name, csv_name in tables.items():
        path = data_dir / csv_name
        if not path.exists():
            print(f"Skipping {table_name}: {path} not found")
            continue
        count = load_csv_to_table(path, table_name, if_exists=if_exists)
        print(f"Loaded {count} rows into {table_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load pipeline CSVs into PostgreSQL.")
    parser.add_argument(
        "--table",
        help="Single table name (e.g. supply_events_enriched). Default: load all known tables.",
    )
    parser.add_argument("--csv", help="CSV path (required with --table if not a known table)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument(
        "--if-exists",
        choices=["replace", "append", "fail"],
        default="replace",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if args.table:
        csv_path = Path(args.csv) if args.csv else data_dir / f"{args.table}.csv"
        if not csv_path.exists():
            raise SystemExit(f"CSV not found: {csv_path}")
        count = load_csv_to_table(csv_path, args.table, if_exists=args.if_exists)
        print(f"Loaded {count} rows into {args.table}")
    else:
        load_all(data_dir, if_exists=args.if_exists)


if __name__ == "__main__":
    main()
