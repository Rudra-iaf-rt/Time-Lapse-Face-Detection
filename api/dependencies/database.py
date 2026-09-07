# api/dependencies/database.py
"""Application lifecycle and FastAPI dependencies for data stores."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Any

import yaml

from database.postgres_manager import PostgresManager
from database.qdrant_manager import QdrantManager
from database.redis_manager import RedisManager
from database.identity_store import IdentityStore

logger = logging.getLogger(__name__)

_config: Optional[dict] = None
_postgres: Optional[PostgresManager] = None
_qdrant: Optional[QdrantManager] = None
_redis: Optional[RedisManager] = None
_identity_store: Optional[IdentityStore] = None
_search_engine = None

_postgres_ok = False
_qdrant_ok = False
_redis_ok = False


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config() -> dict:
    global _config
    if _config is not None:
        return _config

    config_path = os.environ.get("CONFIG_PATH", str(_project_root() / "config.yaml"))
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Environment overrides (never hardcode production secrets)
    pg = cfg.setdefault("postgres", {})
    pg["host"] = os.environ.get("POSTGRES_HOST", pg.get("host", "localhost"))
    pg["port"] = int(os.environ.get("POSTGRES_PORT", pg.get("port", 5432)))
    pg["database"] = os.environ.get("POSTGRES_DB", pg.get("database", "multicam_reid"))
    pg["user"] = os.environ.get("POSTGRES_USER", pg.get("user", "postgres"))
    if os.environ.get("POSTGRES_PASSWORD") is not None:
        pg["password"] = os.environ["POSTGRES_PASSWORD"]

    qd = cfg.setdefault("qdrant", {})
    qd["host"] = os.environ.get("QDRANT_HOST", qd.get("host", "localhost"))
    qd["port"] = int(os.environ.get("QDRANT_PORT", qd.get("port", 6333)))

    rd = cfg.setdefault("redis", {})
    rd["host"] = os.environ.get("REDIS_HOST", rd.get("host", "localhost"))
    rd["port"] = int(os.environ.get("REDIS_PORT", rd.get("port", 6379)))
    if os.environ.get("REDIS_PASSWORD"):
        rd["password"] = os.environ["REDIS_PASSWORD"]

    db = cfg.setdefault("database", {})
    db["path"] = os.environ.get("REID_DB_PATH", db.get("path", "database/identities.db"))

    _config = cfg
    return _config


async def init_db() -> None:
    """Initialize managers. Failures are recorded; process stays up for /live."""
    global _postgres, _qdrant, _redis, _identity_store
    global _postgres_ok, _qdrant_ok, _redis_ok, _search_engine

    cfg = load_config()

    sqlite_path = cfg.get("database", {}).get("path", "database/identities.db")
    _identity_store = IdentityStore(db_path=sqlite_path)

    _postgres = PostgresManager(cfg)
    try:
        await _postgres.initialize()
        _postgres_ok = True
    except Exception as exc:
        _postgres_ok = False
        logger.error("PostgreSQL init failed: %s", exc)

    _qdrant = QdrantManager(cfg)
    try:
        _qdrant.initialize()
        _qdrant_ok = True
    except Exception as exc:
        _qdrant_ok = False
        logger.error("Qdrant init failed: %s", exc)

    _redis = RedisManager(cfg)
    try:
        await _redis.initialize()
        _redis_ok = True
    except Exception as exc:
        _redis_ok = False
        logger.error("Redis init failed: %s", exc)

    try:
        from search.query_engine import QueryEngine

        _search_engine = QueryEngine(db_path=sqlite_path)
    except Exception as exc:
        _search_engine = None
        logger.error("Search engine init failed: %s", exc)


async def close_db() -> None:
    global _postgres_ok, _qdrant_ok, _redis_ok
    if _postgres is not None:
        try:
            await _postgres.close()
        except Exception as exc:
            logger.error("PostgreSQL close error: %s", exc)
    if _redis is not None:
        try:
            await _redis.close()
        except Exception as exc:
            logger.error("Redis close error: %s", exc)
    _postgres_ok = False
    _qdrant_ok = False
    _redis_ok = False


def dependency_status() -> dict:
    return {
        "postgresql": "ok" if _postgres_ok else "unavailable",
        "qdrant": "ok" if _qdrant_ok else "unavailable",
        "redis": "ok" if _redis_ok else "unavailable",
    }


def is_ready() -> bool:
    return _postgres_ok and _qdrant_ok and _redis_ok


async def get_db_manager() -> PostgresManager:
    if _postgres is None or not _postgres_ok:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL is unavailable",
        )
    return _postgres


async def get_qdrant_manager() -> QdrantManager:
    if _qdrant is None or not _qdrant_ok:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant is unavailable",
        )
    return _qdrant


async def get_redis_manager() -> RedisManager:
    if _redis is None or not _redis_ok:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        )
    return _redis


def get_identity_store() -> IdentityStore:
    if _identity_store is None:
        cfg = load_config()
        return IdentityStore(db_path=cfg.get("database", {}).get("path", "database/identities.db"))
    return _identity_store


def get_search_engine():
    if _search_engine is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search engine is unavailable",
        )
    return _search_engine


def get_managers_raw() -> dict[str, Any]:
    """For health/admin — returns instances even if unhealthy."""
    return {
        "postgres": _postgres,
        "qdrant": _qdrant,
        "redis": _redis,
        "identity_store": _identity_store,
    }
