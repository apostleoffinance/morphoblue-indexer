#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example — edit passwords before production use."
  cp .env.example .env
  echo "Edit deploy/.env then re-run: ./setup.sh"
  exit 1
fi

# shellcheck disable=SC1091
source .env

HTTP_ONLY="${HTTP_ONLY:-false}"

if [[ "$HTTP_ONLY" == "true" ]]; then
  echo "HTTP-only mode — Metabase at http://YOUR_VPS_IP"
  cp Caddyfile.http Caddyfile.active
else
  if [[ -z "${METABASE_DOMAIN:-}" || "$METABASE_DOMAIN" == "metabase.example.com" ]]; then
    echo "Set METABASE_DOMAIN and ACME_EMAIL in .env, or set HTTP_ONLY=true for IP access."
    exit 1
  fi
  echo "HTTPS mode — Metabase at https://${METABASE_DOMAIN}"
  cp Caddyfile Caddyfile.active
fi

# Mount active Caddyfile
export COMPOSE_FILE=docker-compose.vps.yml

docker compose --env-file .env up -d

echo ""
echo "Waiting for Metabase to become healthy (may take 1–2 minutes on first boot)..."
for i in $(seq 1 30); do
  if docker compose exec -T metabase curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
    echo "Metabase is ready."
    break
  fi
  sleep 5
done

echo ""
docker compose ps
echo ""
if [[ "$HTTP_ONLY" == "true" ]]; then
  echo "Open: http://$(curl -sf ifconfig.me 2>/dev/null || echo YOUR_VPS_IP)"
else
  echo "Open: https://${METABASE_DOMAIN}"
fi
echo ""
echo "Add Postgres in Metabase: host=postgres, port=5432, db=${POSTGRES_DB:-morpho}"
