"""SQLAlchemy column types for Morpho pipeline tables.

On-chain uint256 values (assets, shares, amounts, lltv) must use NUMERIC,
not BIGINT — they often exceed PostgreSQL bigint max (~9.2e18).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, MetaData, Numeric, String, Table, Column

# On-chain integers (Solidity uint256). Max ~78 decimal digits.
UINT256 = Numeric(78, 0)

# Human-readable token amounts after decimal normalization.
NORMALIZED_AMOUNT = Numeric(38, 18)

# Columns that hold raw on-chain uint256 values.
UINT256_COLUMNS = frozenset({"assets", "shares", "amounts", "lltv"})

NORMALIZED_COLUMNS = frozenset({"normalized_assets"})

INTEGER_COLUMNS = frozenset({
    "transaction_index",
    "log_index",
    "transaction_log_index",
    "loan_decimals",
    "decimals",
})

BIGINT_COLUMNS = frozenset({"block_number"})

STRING_COLUMNS = frozenset({
    "chain",
    "event",
    "address",
    "block_timestamp",
    "block_hash",
    "transaction_hash",
    "supplier",
    "caller",
    "borrower",
    "repayer",
    "on_behalf",
    "receiver",
    "market_id",
    "loan_token",
    "collateral_token",
    "loan_symbol",
    "collateral_symbol",
    "oracle",
    "irm",
    "token_address",
    "symbol",
    "name",
})


def sqlalchemy_type_for_column(column: str):
    if column in UINT256_COLUMNS:
        return UINT256
    if column in NORMALIZED_COLUMNS:
        return NORMALIZED_AMOUNT
    if column in BIGINT_COLUMNS:
        return BigInteger()
    if column in INTEGER_COLUMNS:
        return Integer()
    return String()


def dtype_map_for_csv(columns: list[str]) -> dict[str, type]:
    """Pandas read_csv dtypes — load uint256 columns as str to avoid float overflow."""
    return {col: str for col in columns if col in UINT256_COLUMNS}


def sqlalchemy_dtypes_for_columns(columns: list[str]) -> dict[str, object]:
    return {col: sqlalchemy_type_for_column(col) for col in columns}


def build_table(table_name: str, columns: list[str], metadata: MetaData | None = None) -> Table:
    metadata = metadata or MetaData()
    return Table(
        table_name,
        metadata,
        *[Column(col, sqlalchemy_type_for_column(col)) for col in columns],
    )
