# scripts/sync_sqlite_to_postgres.py
"""Sync IdentityStore (SQLite) persons into PostgreSQL for the FastAPI/React path.

Does not delete SQLite data. Uses global_id as the canonical key.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from database.identity_store import IdentityStore
from database.postgres_manager import PostgresManager


def load_cfg() -> dict:
    cfg_path = os.environ.get("CONFIG_PATH", str(ROOT / "config.yaml"))
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    pg = cfg.setdefault("postgres", {})
    pg["host"] = os.environ.get("POSTGRES_HOST", pg.get("host", "localhost"))
    pg["port"] = int(os.environ.get("POSTGRES_PORT", pg.get("port", 5433)))
    pg["database"] = os.environ.get("POSTGRES_DB", pg.get("database", "multicam_reid"))
    pg["user"] = os.environ.get("POSTGRES_USER", pg.get("user", "postgres"))
    if os.environ.get("POSTGRES_PASSWORD") is not None:
        pg["password"] = os.environ["POSTGRES_PASSWORD"]
    return cfg


def _ts(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))
    if isinstance(value, datetime):
        return value
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def sync(db_path: str, limit: int | None = None) -> dict:
    cfg = load_cfg()
    store = IdentityStore(db_path=db_path)
    rows = store.get_all()
    if limit is not None:
        rows = rows[:limit]

    pg = PostgresManager(cfg)
    await pg.initialize()

    created = updated = skipped = 0
    try:
        for row in rows:
            global_id = row.get("global_id")
            if not global_id:
                skipped += 1
                continue
            existing = await pg.get_person(global_id)
            payload = {
                "global_id": global_id,
                "first_seen": _ts(row.get("first_seen") or row.get("first_seen_at")),
                "last_seen": _ts(row.get("last_seen") or row.get("last_seen_at")),
                "confidence": float(row.get("confidence") or row.get("match_score") or 0.5),
                "metadata": {
                    "status": row.get("status"),
                    "last_camera": row.get("last_camera") or row.get("last_camera_id"),
                    "source": "identity_store_sync",
                },
            }
            if existing:
                await pg.update_person(
                    global_id,
                    {
                        "last_seen": payload["last_seen"],
                        "confidence": payload["confidence"],
                        "metadata": payload["metadata"],
                    },
                )
                updated += 1
            else:
                await pg.create_person(payload)
                created += 1
    finally:
        await pg.close()

    return {"created": created, "updated": updated, "skipped": skipped, "total": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync SQLite IdentityStore → PostgreSQL")
    parser.add_argument("--db", default="database/identities.db")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    result = asyncio.run(sync(args.db, args.limit))
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
