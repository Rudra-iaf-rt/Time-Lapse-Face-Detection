# api/routes/admin.py
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.response import ResponseModel
from api.dependencies.database import (
    dependency_status,
    get_managers_raw,
    get_identity_store,
    is_ready,
)
from api.dependencies.auth import require_roles, Role, UserPublic
from database.identity_store import IdentityStore
from database.migrations import migration_status_message

router = APIRouter()


@router.get("/admin/health-detail", response_model=ResponseModel)
async def admin_health_detail(
    _: UserPublic = Depends(require_roles(Role.ADMIN)),
):
    deps = dependency_status()
    managers = get_managers_raw()
    detail = {
        "ready": is_ready(),
        "dependencies": deps,
        "postgres_initialized": managers["postgres"] is not None
        and getattr(managers["postgres"], "_initialized", False),
        "qdrant_initialized": managers["qdrant"] is not None
        and getattr(managers["qdrant"], "_initialized", False),
        "redis_initialized": managers["redis"] is not None
        and getattr(managers["redis"], "_initialized", False),
        "migrations": migration_status_message(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    return ResponseModel(success=True, data=detail)


@router.get("/admin/identity-stats", response_model=ResponseModel)
async def identity_stats(
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    try:
        return ResponseModel(success=True, data=store.stats())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/admin/cache/flush-person/{global_id}", response_model=ResponseModel)
async def flush_person_cache(
    global_id: str,
    _: UserPublic = Depends(require_roles(Role.ADMIN)),
):
    managers = get_managers_raw()
    redis = managers.get("redis")
    if redis is None or not getattr(redis, "_initialized", False):
        raise HTTPException(status_code=503, detail="Redis unavailable")
    await redis.cache_delete(f"person:{global_id}")
    return ResponseModel(success=True, message=f"Cache flush requested for {global_id}")


@router.get("/admin/users/me", response_model=ResponseModel)
async def admin_me(user: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR, Role.VIEWER))):
    return ResponseModel(
        success=True,
        data={"username": user.username, "role": user.role.value},
    )
