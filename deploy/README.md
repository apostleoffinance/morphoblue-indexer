# Morpho Blue Len — VPS deployment (Docker)

Deploy **PostgreSQL** (analytics warehouse) and **Metabase** on a Linux VPS using Docker Compose.

```text
Internet
   │
   ▼
Caddy (:443 TLS)  ──►  Metabase (:3000)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
            metabase-db            postgres
         (Metabase app DB)    (analytics warehouse)
```

---

## Requirements

- Ubuntu 22.04+ / Debian 12+ VPS (1 GB RAM minimum; **2 GB+ recommended**)
- Docker Engine + Docker Compose v2
- Domain name pointed at the VPS IP (for HTTPS), **or** IP-only HTTP access
- Analytics data loaded into Postgres (from local pipeline or run pipeline on VPS)

---

## 1. Prepare the VPS

SSH into your server:

```bash
ssh root@YOUR_VPS_IP
```

Install Docker (official script):

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

Create an app user (recommended):

```bash
adduser morpho
usermod -aG docker morpho
su - morpho
```

---

## 2. Clone the repo

```bash
git clone https://github.com/YOUR_USER/decoded_logs.git
cd decoded_logs/deploy
```

---

## 3. Configure environment

```bash
cp .env.example .env
nano .env
```

Set strong passwords and your domain:

```bash
POSTGRES_USER=morpho
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=morpho

METABASE_DB_PASSWORD=<strong-random-password>

# For HTTPS (recommended)
METABASE_DOMAIN=metabase.yourdomain.com
ACME_EMAIL=you@yourdomain.com

# Set to "true" for IP-only HTTP (no TLS) — not recommended for production
HTTP_ONLY=false
```

Generate passwords:

```bash
openssl rand -base64 32
```

---

## 4. DNS

Point an **A record** at your VPS IP:

```text
metabase.yourdomain.com  →  YOUR_VPS_IP
```

Wait for DNS propagation before starting (check with `dig metabase.yourdomain.com`).

---

## 5. Start services

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
docker compose -f docker-compose.vps.yml --env-file .env up -d
docker compose -f docker-compose.vps.yml ps
```

You should see: `postgres`, `metabase-db`, `metabase`, `caddy` — all running.

---

## 6. First-time Metabase setup

Open in browser:

- **With domain:** `https://metabase.yourdomain.com`
- **HTTP only:** `http://YOUR_VPS_IP`

1. Create admin account  
2. **Add database → PostgreSQL**

| Field | Value |
|-------|--------|
| Host | `postgres` |
| Port | `5432` |
| Database name | `morpho` |
| Username | value of `POSTGRES_USER` from `.env` |
| Password | value of `POSTGRES_PASSWORD` from `.env` |

3. Click **Sync database schema now**

4. **Browse data** → open any table (e.g. `borrow_events_enriched`, `fact_market_activity`) → **X-ray** to explore. No saved dashboard required — see `docs/assets/metabase-dashboard.png` in the repo for a sample view.

---

## 7. Load analytics data onto the VPS

Postgres on the VPS starts **empty**. Load data from your dev machine after running the pipeline locally.

### Option A — pg_dump / pg_restore (recommended)

On your **local machine** (after `uv run python -m flows.daily_pipeline`):

```bash
# Dump local warehouse
pg_dump -h localhost -p 5433 -U morpho -Fc morpho > morpho.dump

# Copy to VPS
scp morpho.dump morpho@YOUR_VPS_IP:~/

# On VPS — restore into Docker Postgres
ssh morpho@YOUR_VPS_IP
cd decoded_logs/deploy
docker compose -f docker-compose.vps.yml exec -T postgres pg_restore \
  -U morpho -d morpho --clean --if-exists < ~/morpho.dump
```

If `pg_restore` errors on `--clean`, drop and recreate:

```bash
docker compose -f docker-compose.vps.yml exec postgres \
  psql -U morpho -d postgres -c "DROP DATABASE morpho;"
docker compose -f docker-compose.vps.yml exec postgres \
  psql -U morpho -d postgres -c "CREATE DATABASE morpho;"
docker compose -f docker-compose.vps.yml exec -T postgres pg_restore \
  -U morpho -d morpho < ~/morpho.dump
```

### Option B — Run pipeline on the VPS

Clone repo on VPS, configure `.env` with RPC keys, install `uv`, run:

```bash
uv sync
docker compose -f deploy/docker-compose.vps.yml up -d postgres
# Point database/connection.py or env at VPS postgres, then:
uv run python -m flows.daily_pipeline
```

For Option B, expose postgres to localhost only on VPS (`127.0.0.1:5433:5432` in compose) for the loader.

---

## 8. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Do **not** expose Postgres (5432) to the public internet.

---

## 9. Operations

```bash
cd decoded_logs/deploy

# Status
docker compose -f docker-compose.vps.yml ps

# Logs
docker compose -f docker-compose.vps.yml logs -f metabase

# Restart Metabase
docker compose -f docker-compose.vps.yml restart metabase

# Update images
docker compose -f docker-compose.vps.yml pull
docker compose -f docker-compose.vps.yml up -d

# Stop everything
docker compose -f docker-compose.vps.yml down

# Stop but keep data volumes
docker compose -f docker-compose.vps.yml down
# Remove volumes (destructive):
# docker compose -f docker-compose.vps.yml down -v
```

---

## 10. Troubleshooting

| Issue | Fix |
|-------|-----|
| Metabase won't start | Check logs: `docker compose logs metabase`. Ensure 2 GB+ RAM. |
| HTTPS certificate fails | Verify DNS A record, ports 80/443 open, `METABASE_DOMAIN` correct |
| Empty tables in Metabase | Restore pg_dump or run pipeline; re-sync schema in Metabase |
| Can't connect to postgres from Metabase | Use host `postgres`, port `5432` (Docker network name) |
| Caddy 502 | Wait for Metabase health (~60s on first boot) |

---

## Files

| File | Purpose |
|------|---------|
| `docker-compose.vps.yml` | Production stack |
| `.env.example` | Environment template |
| `Caddyfile` | Reverse proxy + TLS |
| `setup.sh` | One-command bootstrap |

Local development continues to use the root `docker-compose.yml` (Postgres on port 5433).
