# Morpho Blue Len

## Project Overview

`Morpho Blue Len` is a multi-chain data pipeline for monitoring utilization, liquidity, concentration, and risk metrics across Morpho Blue markets.

The current implementation focuses on extracting and normalizing Morpho event data from Ethereum and compatible chains, then exporting structured CSV output for analytics.

## What it does today

- loads chain configuration from `config.py`
- creates a Web3 contract instance via `contract_loader.py`
- reads Morpho Blue `Supply`, `Borrow`, `Repay`, and `Withdraw` events via extractor modules
- enriches each event with block timestamp and normalized market identifiers
- exports normalized data to `data/*.csv` through `main.py`

## Key Features

- multi-chain support via environment-configured RPC endpoints, including Infura and Alchemy fallbacks
- reusable contract loader for ABI-based contract decoding
- normalized event output across `Supply`, `Borrow`, `Repay`, and `Withdraw`
- timestamp enrichment with block-level caching to avoid redundant RPC calls
- normalized market identifier formatting to `0x...`
- time-based analytics readiness via `block_timestamp`

## Project Structure

- `main.py`
  - orchestrator CLI that fetches event data, normalizes it, and writes CSV output
- `config.py`
  - chain settings, RPC endpoints, and contract addresses for supported networks
- `contract_loader.py`
  - loads the Morpho Blue ABI and initializes `Web3` for a selected chain
- `extractors/supply.py`
  - fetches `Supply` events and normalizes raw event objects into row dictionaries
- `extractors/borrow.py`
  - fetches `Borrow` events and normalizes raw event objects into row dictionaries
- `extractors/repay.py`
  - fetches `Repay` events and normalizes raw event objects into row dictionaries
- `extractors/withdraw.py`
  - fetches `Withdraw` events and normalizes raw event objects into row dictionaries
- `abi/morpho_blue.json`
  - Morpho Blue contract ABI used for event decoding
- `data/`
  - target directory for generated output CSV files
- `README.md`
  - project description and usage notes

## Usage

1. Create a `.env` file with your RPC endpoints:

```bash
MM_INFURA_URL=https://mainnet.infura.io/v3/<your-key>
MM_ALCHEMY_URL=https://eth-mainnet.g.alchemy.com/v2/<your-key>
```

2. Run the orchestrator from the repo root.

Generate all supported event CSVs:

```bash
python main.py --event all --chain ethereum --from-block 22800000 --to-block 22801000
```

Generate one event CSV at a time:

```bash
python main.py --event supply --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event borrow --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event repay --chain ethereum --from-block 22800000 --to-block 22801000
python main.py --event withdraw --chain ethereum --from-block 22800000 --to-block 22801000
```

Specify a custom output path:

```bash
python main.py --event repay --chain ethereum --from-block 22800000 --to-block 22801000 --output data/my_repay.csv
```

Default CSV outputs:

- `data/supply_events.csv`
- `data/borrow_events.csv`
- `data/repay_events.csv`
- `data/withdraw_events.csv`

## Roadmap

Next steps for the pipeline include:

- aggregate supply, borrow, repay, and withdraw metrics per market
- compute utilization ratios, concentration, and risk indicators
- support additional chains beyond Ethereum
- add scheduled ingestion, incremental block range processing, and resume support

## Notes

This repository is designed as a modular event-extraction pipeline for Morpho Blue analytics, with a clear separation between chain configuration, contract loading, event extraction, and output export.
