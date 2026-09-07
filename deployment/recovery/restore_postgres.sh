#!/usr/bin/env bash
# Restore PostgreSQL from a dump. DESTRUCTIVE — requires CONFIRM=yes.
set -euo pipefail

CONFIRM="${CONFIRM:-}"
DUMP_FILE="${1:-}"

if [[ -z "$DUMP_FILE" ]]; then
  echo "Usage: CONFIRM=yes $0 <dump.sql>"
  exit 1
fi

if [[ "$CONFIRM" != "yes" ]]; then
  echo "Refusing to restore without CONFIRM=yes"
  exit 1
fi

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
DB="${POSTGRES_DB:-multicam_reid}"

echo "Restoring $DUMP_FILE into ${DB} on ${HOST}"
PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -f "$DUMP_FILE"
echo "Restore complete"
