#!/usr/bin/env bash
# Backup PostgreSQL. Requires confirmation for overwrite targets.
set -euo pipefail

CONFIRM="${CONFIRM:-}"
OUT_DIR="${OUT_DIR:-./backups}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_FILE="${OUT_DIR}/postgres_${STAMP}.sql"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_FILE" && "$CONFIRM" != "yes" ]]; then
  echo "Refusing to overwrite $OUT_FILE without CONFIRM=yes"
  exit 1
fi

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
DB="${POSTGRES_DB:-multicam_reid}"

echo "Backing up ${USER}@${HOST}:${PORT}/${DB} -> ${OUT_FILE}"
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -F p > "$OUT_FILE"
echo "Done: $OUT_FILE"
