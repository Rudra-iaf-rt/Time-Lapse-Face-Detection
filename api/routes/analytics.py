# api/routes/analytics.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
import sqlalchemy as sa

from api.schemas.response import ResponseModel
from api.dependencies.database import get_db_manager, get_identity_store
from api.dependencies.auth import get_current_user, UserPublic
from database.postgres_manager import PostgresManager
from database.identity_store import IdentityStore
from database.models import CrowdMetric, Anomaly, Observation

router = APIRouter()


@router.get("/analytics/occupancy", response_model=ResponseModel)
async def occupancy(
    camera_id: Optional[int] = None,
    hours: int = Query(24, gt=0, le=168),
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    async with db.get_session() as session:
        q = sa.select(CrowdMetric).where(CrowdMetric.timestamp >= start).where(CrowdMetric.timestamp <= end)
        if camera_id is not None:
            q = q.where(CrowdMetric.camera_id == camera_id)
        q = q.order_by(CrowdMetric.timestamp.desc()).limit(500)
        rows = (await session.execute(q)).scalars().all()
        data = [r.to_dict() for r in rows]
    return ResponseModel(
        success=True,
        data=data,
        message=None if data else "No crowd metrics in PostgreSQL for this window",
    )


@router.get("/analytics/dwell", response_model=ResponseModel)
async def dwell_time(
    global_id: Optional[str] = None,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    """Dwell / visit duration from SQLite IdentityStore when available."""
    try:
        if global_id:
            person = store.get_person(global_id)
            if not person:
                raise HTTPException(status_code=404, detail=f"Person {global_id} not found")
            return ResponseModel(success=True, data={"global_id": global_id, "person": person})

        persons = store.get_all()
        summary = []
        for p in persons[:200]:
            summary.append(
                {
                    "global_id": p.get("global_id"),
                    "first_seen": p.get("first_seen"),
                    "last_seen": p.get("last_seen"),
                    "status": p.get("status"),
                    "last_camera": p.get("last_camera"),
                }
            )
        return ResponseModel(success=True, data=summary)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/analytics/entry-exit", response_model=ResponseModel)
async def entry_exit(
    camera_id: Optional[int] = None,
    hours: int = Query(24, gt=0, le=168),
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    async with db.get_session() as session:
        q = sa.select(CrowdMetric).where(CrowdMetric.timestamp >= start).where(CrowdMetric.timestamp <= end)
        if camera_id is not None:
            q = q.where(CrowdMetric.camera_id == camera_id)
        rows = (await session.execute(q.order_by(CrowdMetric.timestamp))).scalars().all()
        series = [
            {
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "camera_id": r.camera_id,
                "entry_rate": r.entry_rate,
                "exit_rate": r.exit_rate,
                "occupancy": r.occupancy,
            }
            for r in rows
        ]
    return ResponseModel(success=True, data=series)


@router.get("/analytics/routes", response_model=ResponseModel)
async def routes(
    global_id: Optional[str] = None,
    db: PostgresManager = Depends(get_db_manager),
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    if global_id:
        timeline = await db.get_person_timeline(global_id)
        if not timeline.get("events"):
            # SQLite fallback
            person = store.get_person(global_id)
            sightings = store.get_sightings(global_id) if hasattr(store, "get_sightings") else []
            return ResponseModel(
                success=True,
                data={
                    "global_id": global_id,
                    "cameras_visited": timeline.get("cameras_visited", []),
                    "person": person,
                    "sightings": sightings,
                },
            )
        return ResponseModel(success=True, data=timeline)

    return ResponseModel(
        success=True,
        data={"message": "Provide global_id to retrieve a camera journey"},
    )


@router.get("/analytics/anomalies", response_model=ResponseModel)
async def anomalies(
    limit: int = Query(50, gt=0, le=500),
    _: UserPublic = Depends(get_current_user),
):
    from api.dependencies.database import get_managers_raw, dependency_status

    status_map = dependency_status()
    db = get_managers_raw().get("postgres")
    if status_map.get("postgresql") != "ok" or db is None:
        return ResponseModel(
            success=True,
            data=[],
            message="PostgreSQL unavailable — anomaly table not queried",
        )
    async with db.get_session() as session:
        q = sa.select(Anomaly).order_by(Anomaly.detected_at.desc()).limit(limit)
        rows = (await session.execute(q)).scalars().all()
        data = [r.to_dict() for r in rows]
    return ResponseModel(
        success=True,
        data=data,
        message=None if data else "No anomalies recorded in PostgreSQL",
    )


@router.get("/analytics/summary", response_model=ResponseModel)
async def analytics_summary(
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    from api.dependencies.database import get_managers_raw, dependency_status

    stats = store.stats() if hasattr(store, "stats") else {}
    cameras = []
    status_map = dependency_status()
    db = get_managers_raw().get("postgres")
    if status_map.get("postgresql") == "ok" and db is not None:
        try:
            cameras = await db.get_all_cameras()
        except Exception:
            cameras = []
    return ResponseModel(
        success=True,
        data={
            "identity_store": stats,
            "camera_count_postgres": len(cameras),
            "postgresql": status_map.get("postgresql"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )
