# database/migrations.py
"""
Alembic-oriented migration helpers.

Creates tables via SQLAlchemy metadata when Alembic is not yet configured.
Preserves SQLite IdentityStore — this module only targets PostgreSQL.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from database.models import Base

logger = logging.getLogger(__name__)

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


async def run_create_all(engine: AsyncEngine) -> None:
    """Create all ORM tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL schema ensured via metadata.create_all")


async def check_connection(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


def alembic_configured() -> bool:
    return ALEMBIC_INI.exists()


def migration_status_message() -> str:
    if alembic_configured():
        return "Alembic configured — use `alembic upgrade head` for versioned migrations."
    return (
        "Alembic not yet configured. Schema is applied via SQLAlchemy create_all at startup. "
        "SQLite IdentityStore (database/identities.db) is untouched."
    )
