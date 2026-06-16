# Morpho Blue Len Analytics

dbt project for DeFi risk and forensic analytics on Morpho Blue pipeline data.

## Prerequisites

1. PostgreSQL running (`docker compose up -d` from repo root)
2. CSV data loaded (`python -m database.load_csv` from repo root)
3. dbt profile at `../.dbt/profiles.yml`

## Commands

Run from this directory:

```bash
dbt parse --profiles-dir ../.dbt
dbt run --profiles-dir ../.dbt
dbt test --profiles-dir ../.dbt
```

## Model layers

```text
sources (PostgreSQL public.*)
  ↓
staging/          — cleaning, casts, lowercased addresses
  ↓
marts/dimensions/ — dim_market, dim_token
marts/facts/      — volume aggregates, fact_market_activity
marts/risk/       — concentration, credit, liquidity risk
```

## Key marts for Morpho Blue Len

| Model | Purpose |
|-------|---------|
| `fact_market_activity` | Combined supply/borrow/repay/withdraw per market |
| `fact_concentration_risk` | Supplier concentration metrics |
| `fact_credit_risk` | Borrow vs repay / outstanding borrow |
| `fact_liquidity_risk` | Supply vs withdraw / net liquidity |

## DAG overview

```text
supply_events_enriched  → stg_supply_events  → fact_supply_volume ─┐
borrow_events_enriched  → stg_borrow_events  → fact_borrow_volume ─┼→ fact_market_activity → fact_credit_risk
repay_events_enriched   → stg_repay_events   → fact_repay_volume  ─┤                      → fact_liquidity_risk
withdraw_events_enriched→ stg_withdraw_events→ fact_withdraw_volume┘
stg_supply_events → fact_concentration_risk

market_lookup + token_lookup → dim_market
token_lookup → dim_token
```
