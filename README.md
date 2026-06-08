# Morpho Blue Len

## Project Overview

`Morpho Blue Len` is a multi-chain data pipeline for monitoring utilization, liquidity, concentration, and risk metrics across Morpho Blue markets.

The current implementation focuses on extracting and normalizing Morpho event data from Ethereum and compatible chains, then exporting structured CSV output for analytics.

## What it does today

- loads chain configuration from `config.py`
- creates a Web3 contract instance via `contract_loader.py`
- reads Morpho Blue `Supply` events using `extractors/supply.py`
- enriches each event with block timestamp and normalized market identifiers
- exports normalized data to `data/supply_events.csv` through `main.py`

## Key Features

- multi-chain chain support via environment-configured RPC endpoints
- reusable contract loader for ABI-based contract decoding
- normalized supply event output with fields such as:
  - `chain`
  - `event`
  - `address`
  - `block_number`
  - `block_timestamp`
  - `transaction_hash`
  - `supplier`
  - `caller`
  - `assets`
  - `shares`
  - `market_id`

- explicit `market_id` formatting to `0x...`
- time-based analytics readiness via `block_timestamp`

## Project Structure

- `main.py`
  - orchestrator CLI that fetches supply events, normalizes them, and writes CSV output
- `config.py`
  - chain settings, RPC endpoints, and contract addresses for supported networks
- `contract_loader.py`
  - loads the Morpho Blue ABI and initializes `Web3` for a selected chain
- `extractors/supply.py`
  - fetches `Supply` events and normalizes raw event objects into row dictionaries
- `abi/morpho_blue.json`
  - Morpho Blue contract ABI used for event decoding
- `data/`
  - target directory for generated output CSV files
- `README.md`
  - project description and usage notes

## Usage

Run the orchestrator from the repo root:

```bash
python main.py --chain ethereum --from-block 22800000 --to-block 22801000
```

Output is written to `data/supply_events.csv` by default.

## Roadmap

Next steps for the pipeline include:

- add extractors for `borrow`, `repay`, and `withdraw` events
- aggregate supply, borrow, and liquidity metrics per market
- compute utilization ratios, concentration, and risk indicators
- support additional chains beyond Ethereum
- add scheduled ingestion and incremental block range processing

## Notes

This repository is designed as a modular event-extraction pipeline for Morpho Blue analytics, with a clear separation between chain configuration, contract loading, event extraction, and output export.
