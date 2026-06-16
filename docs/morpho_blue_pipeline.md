# Morpho Blue Len — Project Report

**Author:** Olaoluwa Tunmise  
**Project:** Multi-chain Morpho Blue analytics pipeline  
**Status:** Complete  

---

## 1. Executive summary

Morpho Blue Len is an end-to-end DeFi analytics pipeline that extracts Morpho Blue on-chain events (Supply, Borrow, Repay, Withdraw), enriches them with market metadata and USD pricing, validates data quality, loads a PostgreSQL warehouse, transforms data with dbt, and exposes metrics through **Metabase** (primary UI) and a **FastAPI** read-only API.

Supported chains: **Ethereum**, **Base**, **Arbitrum**.

Consumption layers:

| Layer | How results are shared |
|-------|------------------------|
| **Screenshots** | `docs/assets/` — Prefect, Metabase, API (primary for reviewers) |
| **Metabase** | `http://localhost:3000` — local Browse data / X-ray (no saved dashboard required) |
| **FastAPI** | `http://localhost:8000/docs` — optional programmatic access |
| **Prefect** | `http://127.0.0.1:4200` — pipeline monitoring |

No custom frontend and no hand-built Metabase dashboards — screenshots document the output; Metabase is for optional local exploration.

---

## 2. Architecture

### 2.1 High-level data flow

```mermaid
flowchart TB
    subgraph OnChain["On-chain"]
        MB[Morpho Blue Contract]
    end

    subgraph Extract["Extraction & enrichment"]
        RPC[RPC Nodes]
        EV[Event decoders]
        MK[Market lookup]
        TK[Token lookup]
        PR[USD price lookup]
        EN[Enrichment]
        VA[Validation]
    end

    subgraph Orchestration["Orchestration"]
        PF[Prefect Daily Pipeline]
    end

    subgraph Warehouse["Warehouse & modeling"]
        PG[(PostgreSQL)]
        DBT[dbt marts]
    end

    subgraph Consumption["Consumption"]
        MBT[Metabase]
        API[FastAPI]
    end

    MB --> RPC --> EV --> MK --> TK --> PR --> EN --> VA
    VA --> PF
    PF --> PG --> DBT
    DBT --> MBT
    DBT --> API
```

### 2.2 Prefect task graph (9 tasks)

```mermaid
flowchart LR
    T1[Extract Events] --> T2[Resolve Markets]
    T2 --> T3[Resolve Tokens]
    T3 --> T4[Resolve Token Prices]
    T4 --> T5[Enrich Events]
    T5 --> T6[Validate Pipeline]
    T6 --> T7[Load CSV to PostgreSQL]
    T7 --> T8[Run dbt Models]
    T8 --> T9[Run dbt Tests]
```

| # | Task | Output |
|---|------|--------|
| 1 | Extract Events | `data/*_events.csv` |
| 2 | Resolve Markets | `data/market_lookup.csv` |
| 3 | Resolve Tokens | `data/token_lookup.csv` |
| 4 | Resolve Token Prices | `data/token_prices.csv` |
| 5 | Enrich Events | `data/*_events_enriched.csv` |
| 6 | Validate Pipeline | exit code 0 / parity checks |
| 7 | Load CSV to PostgreSQL | 7 Postgres tables |
| 8 | Run dbt Models | staging, facts, risk, Metabase marts |
| 9 | Run dbt Tests | 78+ data tests |

Set `SKIP_EXTRACT=1` to run only tasks 7–9 (load + dbt).

### 2.3 dbt model layers

```text
sources (PostgreSQL public.*)
  │
  ├── supply_events_enriched  ──► stg_supply_events  ──► fact_supply_volume ──┐
  ├── borrow_events_enriched  ──► stg_borrow_events  ──► fact_borrow_volume ──┤
  ├── repay_events_enriched   ──► stg_repay_events   ──► fact_repay_volume  ──┼──► fact_market_activity
  ├── withdraw_events_enriched──► stg_withdraw_events ──► fact_withdraw_volume┘         │
  │                                                                                        ├──► fact_credit_risk
  ├── market_lookup + token_lookup ──► dim_market, dim_token                              └──► fact_liquidity_risk
  │
  └── stg_supply_events ──► fact_concentration_risk

fact_*_volume ──► mart_supply_activity, mart_borrow_activity
stg_*_events  ──► mart_supplier_totals, mart_borrower_totals
```

---

## 3. Project structure

```text
decoded_logs/
├── main.py                    # CLI orchestrator
├── config.py                  # chains, RPCs, pricing config
├── contract_loader.py         # Web3 + ABI loader
├── abi/                       # Morpho Blue + ERC20 ABIs
├── extractors/                # supply, borrow, repay, withdraw, market, token, price, enrich, validate
├── data/                      # generated CSVs (gitignored in production)
├── database/                  # Postgres schema, connection, CSV loader
├── flows/                     # Prefect daily pipeline + tasks
├── morpho_analytics/          # dbt project
│   └── models/
│       ├── staging/           # stg_*_events (views)
│       └── marts/
│           ├── dimensions/    # dim_market, dim_token
│           ├── facts/         # fact_*_volume, fact_market_activity
│           ├── risk/          # concentration, credit, liquidity
│           └── metabase/      # dashboard-ready aggregates
├── api/                       # FastAPI read-only analytics API
│   ├── main.py
│   ├── protocol.py
│   ├── metrics.py
│   ├── markets.py
│   └── db.py
├── docker-compose.yml         # Postgres + Metabase
└── docs/
    ├── morpho_blue_pipeline.md
    └── assets/                # screenshots
```

---

## 4. Screenshots

### 4.1 Prefect — completed pipeline run

Orchestrated flow run showing extract, lookup, enrich, validate, Postgres load, and dbt steps. Default block range `22800000–22801000` on Ethereum.

![Prefect pipeline run](assets/prefect-run.png)

Sample extract output from logs:

| Event | Rows written |
|-------|-------------|
| Supply | 160 |
| Borrow | 20 |
| Repay | 22 |
| Withdraw | 172 |

### 4.2 Metabase — local exploration (screenshot)

Metabase runs at **http://localhost:3000** after `docker compose up -d`. Connect Postgres (`host: postgres`, port `5432`), then **Browse data** → e.g. `borrow_events_enriched` → **X-ray** for auto-generated charts. You do not need to build saved dashboards chart-by-chart.

Screenshot below shows the X-ray view (distributions by loan symbol, block number, USD amounts). This image is what reviewers see on GitHub; run Metabase locally only if you want to explore live data.

![Metabase exploration](assets/metabase-dashboard.png)

Example local URL (table ID varies per install):

```text
http://localhost:3000/auto/dashboard/table/26?chain=&loan_symbol=
```

> **Note:** Metabase may fail to chart raw `assets` columns (uint256-scale integers). Use `normalized_assets` or `amount_usd` instead.

### 4.3 FastAPI — Swagger UI

Read-only analytics API over dbt marts. Auto-generated OpenAPI docs at `/docs`.

![API Swagger UI](assets/api-swagger.png)

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/protocol/summary` | Protocol-wide USD KPIs |
| GET | `/protocol/activity-by-chain` | Totals by chain |
| GET | `/metrics/supply-by-asset` | Supply bar chart data |
| GET | `/metrics/borrow-by-asset` | Borrow bar chart data |
| GET | `/metrics/top-suppliers` | Top suppliers leaderboard |
| GET | `/metrics/top-borrowers` | Top borrowers leaderboard |
| GET | `/markets` | Paginated market list |
| GET | `/markets/{market_id}` | Market detail + risk marts |

---

## 5. Sample outputs

### 5.1 CSV files (`data/`)

| File | Description | Example row count (default block window) |
|------|-------------|-------------------------------------------|
| `supply_events.csv` | Raw supply events | 160 |
| `borrow_events.csv` | Raw borrow events | 20 |
| `repay_events.csv` | Raw repay events | 22 |
| `withdraw_events.csv` | Raw withdraw events | 172 |
| `market_lookup.csv` | On-chain market params | 94 |
| `token_lookup.csv` | ERC20 metadata | 78 |
| `token_prices.csv` | USD prices per token | 78 |
| `*_events_enriched.csv` | Joined + normalized + USD | same as base event file |

### 5.2 Enriched row example (supply)

Key columns added during enrichment:

| Column | Example | Meaning |
|--------|---------|---------|
| `loan_symbol` | `USDC` | Loan token ticker |
| `collateral_symbol` | `WETH` | Collateral token ticker |
| `normalized_assets` | `50000.0` | Amount in loan token units |
| `price_usd` | `1.0` | Token price at lookup |
| `amount_usd` | `50000.0` | USD value of the event |

### 5.3 API response example (`GET /protocol/summary`)

```json
{
  "market_count": 93,
  "chain_count": 2,
  "total_supply_usd": 44320227.14,
  "total_borrow_usd": 19472253.66,
  "total_repay_usd": 482321.11,
  "total_withdraw_usd": 22633119.72,
  "outstanding_borrow_usd": 18989932.55,
  "net_liquidity_flow_usd": 21687107.42
}
```

Values reflect the **loaded block window**, not full protocol lifetime history.

### 5.4 dbt test output

```text
Done. PASS=78 WARN=0 ERROR=0 SKIP=0 TOTAL=78
```

---

## 6. Example SQL queries

### 6.1 Raw enriched tables (Postgres)

```sql
-- Total supply by asset (USD)
SELECT
    loan_symbol,
    SUM(amount_usd) AS total_supply_usd
FROM supply_events_enriched
GROUP BY loan_symbol
ORDER BY total_supply_usd DESC;
```

```sql
-- Top 20 suppliers
SELECT
    supplier,
    SUM(normalized_assets) AS supplied,
    SUM(amount_usd) AS supplied_usd
FROM supply_events_enriched
GROUP BY supplier
ORDER BY supplied_usd DESC
LIMIT 20;
```

```sql
-- Borrow events in block window with market context
SELECT
    chain,
    block_number,
    event_timestamp,
    loan_symbol,
    collateral_symbol,
    normalized_assets,
    amount_usd,
    market_id
FROM borrow_events_enriched
ORDER BY event_timestamp DESC;
```

### 6.2 dbt staging views

```sql
-- Cleaned supply events (lowercased addresses, typed timestamps)
SELECT
    chain,
    event_timestamp,
    wallet_address,
    loan_symbol,
    amount_normalized,
    amount_usd
FROM stg_supply_events
WHERE chain = 'ethereum'
ORDER BY event_timestamp DESC
LIMIT 50;
```

### 6.3 dbt fact and risk marts

```sql
-- Market activity overview (USD)
SELECT
    chain,
    loan_symbol,
    total_supply_volume_usd,
    total_borrow_volume_usd,
    outstanding_borrow_usd,
    net_liquidity_flow_usd
FROM fact_market_activity
ORDER BY total_supply_volume_usd DESC;
```

```sql
-- Supplier concentration risk
SELECT
    chain,
    loan_symbol,
    largest_supplier_pct,
    top_5_supplier_pct,
    unique_suppliers
FROM fact_concentration_risk
WHERE largest_supplier_pct > 0.5
ORDER BY largest_supplier_pct DESC;
```

```sql
-- Credit risk — repayment ratio by market
SELECT
    chain,
    loan_symbol,
    total_borrow,
    total_repay,
    outstanding_borrow,
    repayment_ratio
FROM fact_credit_risk
ORDER BY outstanding_borrow DESC;
```

### 6.4 Metabase-ready marts

```sql
-- Dashboard: supply by asset
SELECT loan_symbol, total_supply, total_supply_usd
FROM mart_supply_activity
ORDER BY total_supply_usd DESC;

-- Dashboard: borrow by asset
SELECT loan_symbol, total_borrow, total_borrow_usd
FROM mart_borrow_activity
ORDER BY total_borrow_usd DESC;

-- Dashboard: top borrowers
SELECT borrower, borrowed, borrowed_usd
FROM mart_borrower_totals
ORDER BY borrowed_usd DESC
LIMIT 20;
```

---

## 7. Technology stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Package manager | uv |
| On-chain | web3.py, Morpho Blue ABI |
| Pricing | CoinGecko Pro + DefiLlama |
| Orchestration | Prefect 3 |
| Warehouse | PostgreSQL 17 (Docker) |
| Transform | dbt (dbt-postgres) |
| Visualization | Metabase |
| API | FastAPI + Uvicorn |
| ORM / SQL | SQLAlchemy, pandas |

---

## 8. Setup and run

```bash
# Install
uv sync

# Infrastructure
docker compose up -d

# Configure .env (RPC URLs + GECKO_API_KEY)
# MM_INFURA_URL, MM_ALCHEMY_URL, ARBITRUM_RPC, GECKO_API_KEY

# Full pipeline
export PREFECT_API_URL=http://127.0.0.1:4200/api   # optional
uv run python -m flows.daily_pipeline

# Metabase
open http://localhost:3000

# API (optional)
uv run uvicorn api.main:app --reload --port 8000
open http://localhost:8000/docs
```

**Postgres (host):** `postgresql://morpho:morpho@localhost:5433/morpho`  
**Metabase DB connection (inside Docker):** host `postgres`, port `5432`

### VPS production deployment

For Docker on a Linux VPS with HTTPS, see **[deploy/README.md](../deploy/README.md)**:

```bash
cd deploy && cp .env.example .env && ./setup.sh
```

Stack: analytics Postgres + Metabase app Postgres + Metabase + Caddy (TLS).

---

## 9. Design decisions and limitations

### Decisions

- **CSV as intermediate format** — simple to inspect, replay, and load; all file I/O centralized in `main.py`.
- **Market lookup from union of all events** — avoids missing borrow-only markets in joins.
- **uint256 as NUMERIC(78,0)** — PostgreSQL bigint is insufficient for on-chain integers.
- **Truncate + schema sync on load** — preserves dbt-dependent views while refreshing data.
- **Metabase for local exploration only** — Browse data and X-ray; screenshots in `docs/assets/` document results for GitHub viewers.
- **Snapshot marts** — fact tables aggregate over the loaded window; sufficient for overview queries and API.

### Limitations

- **No time-series marts** — `event_timestamp` exists in staging but facts group by market/asset only. Trend analysis requires daily/hourly dbt models.
- **Block window scope** — default extract is ~1000 blocks (~hours on Ethereum). Totals are window totals, not full protocol history.
- **Price snapshot** — `price_usd` is point-in-time at pipeline run, not historical oracle prices per block.
- **Metabase raw uint256 charts** — visualize `normalized_assets` / `amount_usd` instead of raw `assets`.

---

## 10. Completed scope

- [x] Multi-chain extraction (ethereum, base, arbitrum)
- [x] Market and token on-chain resolution
- [x] USD pricing (CoinGecko + DefiLlama)
- [x] Enrichment, validation, CSV export
- [x] PostgreSQL warehouse + schema-aware loader
- [x] dbt staging, facts, risk, Metabase marts
- [x] Prefect orchestration (9 tasks)
- [x] Metabase local exploration + documentation screenshots
- [x] FastAPI read-only analytics API

### Optional future work

- Incremental block processing and resume
- Time-series marts (daily volume, TVL trends)
- Prefect deployments / scheduled runs
- Historical price feeds per block

---

## 11. References

- [Morpho Blue documentation](https://docs.morpho.org/)
- [dbt project README](../morpho_analytics/README.md)
- [Main README](../README.md)
