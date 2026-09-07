# database/connection_pool.py
"""SQLAlchemy async engine / session pool helpers."""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def build_async_dsn(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    host = host or os.environ.get("POSTGRES_HOST", "localhost")
    port = int(port or os.environ.get("POSTGRES_PORT", 5432))
    database = database or os.environ.get("POSTGRES_DB", "multicam_reid")
    user = user or os.environ.get("POSTGRES_USER", "postgres")
    password = password if password is not None else os.environ.get("POSTGRES_PASSWORD", "postgres")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def create_pool(
    dsn: Optional[str] = None,
    pool_size: int = 10,
    max_overflow: int = 20,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection pooling."""
    url = dsn or build_async_dsn()
    engine = create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    logger.info("Created async connection pool")
    return engine


def create_session_factory(engine: AsyncEngine) -> sessionmaker:
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
