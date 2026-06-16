# Morpho Blue Len

## Project Overview

`Morpho Blue Len` is a multi-chain data pipeline for monitoring utilization, liquidity, concentration, and risk metrics across Morpho Blue markets.

The pipeline extracts on-chain events, resolves market and token metadata, normalizes raw amounts into human-readable values, and exports structured CSV output for analytics.

## Pipeline

```text
RPC
 ↓
Event Decoding (Supply, Borrow, Repay, Withdraw)
 ↓
Market Resolution (union of all event market_ids)
 ↓
Token Resolution (ERC20 symbol, name, decimals)
 ↓
Enrichment (join + normalized_assets)
 ↓
Validation
```

### Fact tables

| File | Description |
|------|-------------|
| `data/supply_events.csv` | Supply events |
| `data/borrow_events.csv` | Borrow events |
| `data/repay_events.csv` | Repay events |
| `data/withdraw_events.csv` | Withdraw events |
| `data/*_events_enriched.csv` | Fact tables joined with market/token dimensions and `normalized_assets` |

### Dimension tables

| File | Description |
|------|-------------|
| `data/market_lookup.csv` | `market_id` → loan/collateral tokens, oracle, IRM, LLTV |
| `data/token_lookup.csv` | Token address → symbol, name, decimals |

## What it does today

- loads chain configuration from `config.py`
- creates a Web3 contract instance via `contract_loader.py`
- reads Morpho Blue `Supply`, `Borrow`, `Repay`, and `Withdraw` events via extractor modules
- enriches each event with block timestamp and normalized market identifiers
- resolves market parameters on-chain from the union of all event `market_id` values
- resolves ERC20 token metadata (`symbol`, `name`, `decimals`) with graceful failure handling
- joins events with market and token dimensions and computes `normalized_assets`
- validates block ranges, market coverage, and enriched/base row parity
- exports all output to `data/*.csv` through `main.py` (extractors do not write CSVs)

## Key Features

- multi-chain support via environment-configured RPC endpoints, including Infura and Alchemy fallbacks
- reusable contract loader for ABI-based contract decoding
- normalized event output across `Supply`, `Borrow`, `Repay`, and `Withdraw`
- timestamp enrichment with block-level caching to avoid redundant RPC calls
- market resolution from all event types (not supply-only), avoiding missing joins on borrow-only markets
- token dimension table with zero-address exclusion and nullable integer decimals
- amount normalization via `Decimal` to avoid float precision issues (e.g. `50000.0` not `49999.99999999999`)
- post-pipeline validation for consistency checks

## Project Structure

- `main.py` — CLI orchestrator; all CSV read/write happens here
- `config.py` — chain settings, RPC endpoints, and Morpho contract addresses
- `contract_loader.py` — loads the Morpho Blue ABI and initializes `Web3` for a selected chain
- `extractors/supply.py` — fetches and normalizes `Supply` events
- `extractors/borrow.py` — fetches and normalizes `Borrow` events
- `extractors/repay.py` — fetches and normalizes `Repay` events
- `extractors/withdraw.py` — fetches and normalizes `Withdraw` events
- `extractors/market_lookup.py` — resolves `market_id` → market params on-chain
- `extractors/token_lookup.py` — resolves token address → ERC20 metadata on-chain
- `extractors/enrich.py` — joins events with market/token dimensions and normalizes amounts
- `extractors/validate.py` — checks block ranges, market coverage, and enriched parity
- `abi/morpho_blue.json` — Morpho Blue contract ABI
- `abi/erc20.json` — minimal ERC20 ABI (`symbol`, `name`, `decimals`)
- `database/` — PostgreSQL load layer (`schema.py`, `load_csv.py`)
- `morpho_analytics/` — dbt project for Morpho Blue Len analytics marts
- `data/` — generated output CSV files

## Setup

1. Create a `.env` file with your RPC endpoints:

```bash
MM_INFURA_URL=https://mainnet.infura.io/v3/<your-key>
MM_ALCHEMY_URL=https://eth-mainnet.g.alchemy.com/v2/<your-key>
```

2. Install dependencies (Python ≥ 3.12):

```bash
uv sync
```

## Usage

Run all commands from the repo root.

### Full pipeline (single chain)

```bash
# 1. Extract all events (same block window)
python main.py --event all --chain ethereum --from-block 22800000 --to-block 22801000

# 2. Resolve markets (union of supply + borrow + repay + withdraw market_ids)
python main.py --event market --chain ethereum

# 3. Resolve tokens from market loan/collateral addresses
python main.py --event token --chain ethereum

# 4. Enrich each event file
python main.py --event enrich --input data/supply_events.csv
python main.py --event enrich --input data/borrow_events.csv
python main.py --event enrich --input data/repay_events.csv
python main.py --event enrich --input data/withdraw_events.csv

# 5. Validate consistency
python main.py --event validate --chain ethereum --from-block 22800000 --to-block 22801000
```

### Multi-chain

`--chain` accepts one or more chains, or `all`. Output CSVs include a `chain` column; re-running a chain replaces that chain's rows in the existing files.

```bash
# All configured chains, same block range (only valid if heights align)
python main.py --event all --chain all --from-block 22800000 --to-block 22801000

# Multiple chains explicitly
python main.py --event all --chain ethereum base --from-block 22800000 --to-block 22801000

# Per-chain block ranges (recommended)
python main.py --event all --chain ethereum base arbitrum \
  --block-range ethereum:22800000-22801000 \
  --block-range base:25000000-25001000 \
  --block-range arbitrum:250000000-250010000

# Resolve dimensions for all chains present in event CSVs
python main.py --event market --chain all
python main.py --event token --chain all

# Validate per chain
python main.py --event validate --chain ethereum base \
  --block-range ethereum:22800000-22801000 \
  --block-range base:25000000-25001000
```

Supported chains: `ethereum`, `base`, `arbitrum` (see `config.py`).

### Extract events

Generate all event CSVs in one run (recommended for consistent block coverage):

```bash
python main.py --event all --chain ethereum --from-block 22800000 --to-block 22801000
```

Generate one event type at a time:

```bash
python main.py --event supply   --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event borrow   --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event repay    --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event withdraw --chain ethereum --from-block 22800000 --to-block 22801000
```

Custom output path:

```bash
python main.py --event repay --chain ethereum --from-block 22800000 --to-block 22801000 --output data/my_repay.csv
```

### Market and token lookup

```bash
# Default: unions market_ids from all four event CSVs in data/
python main.py --event market --chain ethereum

# Custom event inputs (comma-separated)
python main.py --event market --chain ethereum --input data/supply_events.csv,data/borrow_events.csv

# Resolve ERC20 metadata for all tokens in market_lookup.csv
python main.py --event token --chain ethereum
```

### Enrichment

Joins each event file with `market_lookup.csv` and `token_lookup.csv`, adding:

- `loan_token`, `collateral_token`
- `loan_symbol`, `collateral_symbol`
- `loan_decimals`
- `normalized_assets` (`assets / 10**decimals`, using `Decimal` for precision)

```bash
python main.py --event enrich --input data/supply_events.csv
# → data/supply_events_enriched.csv
```

### Validation

Checks:

- block ranges fall within `--from-block` / `--to-block` (when provided)
- every `market_id` in event files exists in `market_lookup.csv`
- each enriched file has the same row count and `transaction_hash` order as its base file
- warns on enriched rows with blank `loan_symbol`

```bash
python main.py --event validate --chain ethereum
python main.py --event validate --chain ethereum --from-block 22800000 --to-block 22801000
```

Exits with code `1` on failure.

## PostgreSQL warehouse

Start Postgres and load enriched CSVs:

```bash
docker compose up -d
python -m database.load_csv
```

On-chain integer columns (`assets`, `shares`, `amounts`, `lltv`) use PostgreSQL `NUMERIC(78, 0)` — not `BIGINT` — because uint256 values exceed bigint max.

| Module | Role |
|--------|------|
| `database/schema.py` | Column type definitions (uint256 → NUMERIC) |
| `database/load_csv.py` | Read CSVs as strings, write with explicit types |
| `database/connection.py` | SQLAlchemy engine |

## dbt analytics (Morpho Blue Len)

After loading CSVs into Postgres, build marts:

```bash
cd morpho_analytics
DBT_PROFILES_DIR=. dbt run
DBT_PROFILES_DIR=. dbt test
```

Layer structure:

```text
staging/           → cleaned events (views)
marts/dimensions/  → dim_market, dim_token
marts/facts/       → volume aggregates, fact_market_activity
marts/risk/        → concentration, credit, liquidity risk
```

See `morpho_analytics/README.md` for the full DAG.

## Default outputs

| Step | Output |
|------|--------|
| supply | `data/supply_events.csv` |
| borrow | `data/borrow_events.csv` |
| repay | `data/repay_events.csv` |
| withdraw | `data/withdraw_events.csv` |
| market | `data/market_lookup.csv` |
| token | `data/token_lookup.csv` |
| enrich | `data/<event>_events_enriched.csv` |

## Analytics examples

On enriched files, `normalized_assets` is denominated in the **loan token**:

```sql
-- Total supply by token
SELECT loan_symbol, SUM(normalized_assets)
FROM supply_events_enriched
GROUP BY loan_symbol;

-- Top borrowed assets
SELECT loan_symbol, SUM(normalized_assets)
FROM borrow_events_enriched
GROUP BY loan_symbol;

-- Market view
SELECT market_id, loan_symbol, collateral_symbol
FROM supply_events_enriched;
```

## Important notes

- **Row counts differ across event types.** Supply, borrow, repay, and withdraw are separate events — 134 supplies and 17 borrows in the same block range is expected.
- **Use `--event all` with one block range** so all event files cover the same window. Re-run market → token → enrich after re-extracting events.
- **Enriched row count must match base.** Each `*_events_enriched.csv` should have one row per row in its `*_events.csv`.
- **Market lookup uses the union of all events** so borrow-only markets are not missing from joins.
- **Multi-chain output lives in the same CSVs**, keyed by the `chain` column. Enrichment joins on `(chain, market_id)` and `(chain, token_address)`.
- **Zero address tokens** (`0x0000...`) are excluded from token resolution.
- **CSV I/O lives in `main.py` only.** Extractor modules return data; the orchestrator handles pandas and file writes.

## Roadmap

- Phase 12: Morpho Blue Len dashboard and API on top of dbt marts
- incremental block range processing and resume support
- scheduled ingestion
- additional chains and oracle price feeds for USD-denominated risk metrics

## Notes

This repository is a modular analytics pipeline for Morpho Blue: chain configuration, contract loading, event extraction, dimension resolution, enrichment, validation, and CSV export are kept in separate layers with `main.py` as the single orchestration entry point.
