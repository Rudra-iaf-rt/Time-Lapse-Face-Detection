# api/routes/persons.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.schemas.person import PersonCreate, PersonUpdate, PersonListResponse
from api.schemas.response import ResponseModel
from api.dependencies.database import (
    get_db_manager,
    get_qdrant_manager,
    get_redis_manager,
    get_identity_store,
)
from api.dependencies.auth import (
    get_current_user,
    require_roles,
    Role,
    UserPublic,
)
from database.postgres_manager import PostgresManager
from database.qdrant_manager import QdrantManager
from database.redis_manager import RedisManager
from database.identity_store import IdentityStore

router = APIRouter()


class NoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


def _dump(model: Any) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


@router.post("/persons", response_model=ResponseModel)
async def create_person(
    person_data: PersonCreate,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    try:
        person = await db.create_person(_dump(person_data))
        return ResponseModel(success=True, message="Person created successfully", data=person)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/persons/{global_id}", response_model=ResponseModel)
async def get_person(
    global_id: str,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    """Get person by global_id from IdentityStore; optionally enrich from Postgres/Redis if up."""
    from api.dependencies.database import get_managers_raw, dependency_status

    sqlite_person = store.get_person(global_id)
    person = None
    cached = None
    managers = get_managers_raw()
    status_map = dependency_status()

    redis = managers.get("redis")
    if status_map.get("redis") == "ok" and redis is not None:
        try:
            cached = await redis.get_cached_person(global_id)
        except Exception:
            cached = None
        if cached:
            return ResponseModel(success=True, data=cached, message="from cache")

    db = managers.get("postgres")
    if status_map.get("postgresql") == "ok" and db is not None:
        try:
            person = await db.get_person(global_id)
        except Exception:
            person = None

    if not person and not sqlite_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {global_id} not found",
        )

    data = {
        "global_id": global_id,
        "postgres": person,
        "identity_store": sqlite_person,
    }
    if status_map.get("redis") == "ok" and redis is not None:
        try:
            await redis.cache_person(global_id, data)
        except Exception:
            pass
    return ResponseModel(success=True, data=data)


@router.put("/persons/{global_id}", response_model=ResponseModel)
async def update_person(
    global_id: str,
    updates: PersonUpdate,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    person = await db.update_person(global_id, _dump(updates))
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {global_id} not found",
        )
    return ResponseModel(success=True, message="Person updated successfully", data=person)


@router.get("/persons", response_model=ResponseModel)
async def list_persons(
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    search: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    """
    List persons. Prefers SQLite IdentityStore (pipeline output).
    Does not require PostgreSQL so legacy data remains accessible.
    """
    items = []
    try:
        rows = store.get_all()
        for row in rows:
            gid = row.get("global_id")
            if search and search.lower() not in str(gid).lower():
                continue
            conf = row.get("confidence") or row.get("match_score")
            if min_confidence is not None and conf is not None and float(conf) < min_confidence:
                continue
            items.append(row)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"IdentityStore list failed: {exc}") from exc

    total = len(items)
    start = (page - 1) * per_page
    page_items = items[start : start + per_page]

    return ResponseModel(
        success=True,
        data={
            "items": page_items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "source": "identity_store",
        },
    )


@router.get("/persons/{global_id}/timeline", response_model=ResponseModel)
async def get_person_timeline(
    global_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: PostgresManager = Depends(get_db_manager),
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    timeline = await db.get_person_timeline(global_id)

    events = timeline.get("events", [])
    if start_time or end_time:
        filtered = []
        for event in events:
            ts = event.get("timestamp")
            if isinstance(ts, str):
                event_time = datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
            else:
                event_time = ts
            if start_time and event_time and event_time < start_time:
                continue
            if end_time and event_time and event_time > end_time:
                continue
            filtered.append(event)
        timeline["events"] = filtered

    # Augment with SQLite events/sightings when PG empty
    if not timeline.get("events"):
        try:
            sqlite_events = store.get_events(global_id)
            sightings = store.get_sightings(global_id)
            timeline["sqlite_events"] = sqlite_events
            timeline["sightings"] = sightings
        except Exception as exc:
            timeline["sqlite_error"] = str(exc)

    return ResponseModel(success=True, data=timeline)


@router.post("/persons/{global_id}/notes", response_model=ResponseModel)
async def add_person_note(
    global_id: str,
    body: NoteBody,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    ok = store.add_note(global_id, body.note)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Person {global_id} not found or note empty")
    return ResponseModel(success=True, message="Note added", data={"global_id": global_id})


@router.post("/persons/{global_id}/resolve", response_model=ResponseModel)
async def resolve_person(
    global_id: str,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    ok = store.resolve(global_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Person {global_id} not found or cannot resolve")
    return ResponseModel(success=True, message="Person resolved", data={"global_id": global_id})


@router.post("/persons/{global_id}/reactivate", response_model=ResponseModel)
async def reactivate_person(
    global_id: str,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    ok = store.reactivate(global_id)
    if not ok:
        raise HTTPException(
            status_code=404, detail=f"Person {global_id} not found or cannot reactivate"
        )
    return ResponseModel(success=True, message="Person reactivated", data={"global_id": global_id})


@router.get("/persons/{global_id}/biometrics", response_model=ResponseModel)
async def get_person_biometrics(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    """Return biometric *metadata* only — never raw embedding vectors in API logs/responses beyond quality fields."""
    profile = await db.get_biometric_profile(global_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Biometric profile for {global_id} not found",
        )
    return ResponseModel(success=True, data=profile)


@router.get("/persons/{global_id}/matches", response_model=ResponseModel)
async def get_person_matches(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    matches = await db.get_identity_matches(global_id)
    return ResponseModel(success=True, data=matches)


@router.delete("/persons/{global_id}", response_model=ResponseModel)
async def delete_person(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager),
    qdrant: QdrantManager = Depends(get_qdrant_manager),
    redis: RedisManager = Depends(get_redis_manager),
    _: UserPublic = Depends(require_roles(Role.ADMIN)),
):
    qdrant.delete_embeddings_for_person(global_id)
    await redis.cache_delete(global_id)
    # Soft-delete path: IdentityStore.delete_identity if present
    return ResponseModel(
        success=True,
        message=f"Vector/cache cleanup done for {global_id}; SQLite row not auto-deleted",
    )
