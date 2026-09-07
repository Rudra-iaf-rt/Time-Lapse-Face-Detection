# api/routes/tracks.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
import sqlalchemy as sa

from api.schemas.response import ResponseModel
from api.schemas.track import TrackCreate, TrackListResponse, TrackResponse
from api.dependencies.database import get_db_manager, get_redis_manager
from api.dependencies.auth import get_current_user, require_roles, Role, UserPublic
from database.postgres_manager import PostgresManager
from database.redis_manager import RedisManager
from database.models import Track, Observation

router = APIRouter()


@router.get("/tracks", response_model=ResponseModel)
async def list_tracks(
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    global_id: Optional[str] = None,
    camera_id: Optional[int] = None,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    async with db.get_session() as session:
        query = sa.select(Track)
        count_q = sa.select(sa.func.count(Track.id))
        if global_id:
            query = query.where(Track.global_id == global_id)
            count_q = count_q.where(Track.global_id == global_id)
        if camera_id is not None:
            query = query.where(Track.camera_id == camera_id)
            count_q = count_q.where(Track.camera_id == camera_id)

        total = (await session.execute(count_q)).scalar() or 0
        query = query.order_by(Track.start_time.desc()).offset((page - 1) * per_page).limit(per_page)
        rows = (await session.execute(query)).scalars().all()
        items = [t.to_dict() for t in rows]

    return ResponseModel(
        success=True,
        data={"items": items, "total": total, "page": page, "per_page": per_page},
    )


@router.get("/tracks/{track_id}", response_model=ResponseModel)
async def get_track(
    track_id: str,
    db: PostgresManager = Depends(get_db_manager),
    redis: RedisManager = Depends(get_redis_manager),
    _: UserPublic = Depends(get_current_user),
):
    # Live cache first
    live = await redis.get_track(track_id)
    async with db.get_session() as session:
        result = await session.execute(sa.select(Track).where(Track.track_id == track_id))
        track = result.scalar_one_or_none()
        if not track and not live:
            raise HTTPException(status_code=404, detail=f"Track {track_id} not found")
        data = track.to_dict() if track else {"track_id": track_id}
        if live:
            data["live"] = live
        return ResponseModel(success=True, data=data)


@router.get("/tracks/{track_id}/observations", response_model=ResponseModel)
async def track_observations(
    track_id: str,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    async with db.get_session() as session:
        result = await session.execute(
            sa.select(Observation)
            .where(Observation.track_id == track_id)
            .order_by(Observation.timestamp)
        )
        obs = [o.to_dict() for o in result.scalars().all()]
    return ResponseModel(success=True, data=obs)


@router.post("/tracks", response_model=ResponseModel)
async def create_track(
    track_data: TrackCreate,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    try:
        created = await db.create_track(track_data.model_dump())
        return ResponseModel(success=True, message="Track created", data=created)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tracks/by-person/{global_id}", response_model=ResponseModel)
async def tracks_by_person(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    tracks = await db.get_tracks_by_person(global_id)
    return ResponseModel(success=True, data=tracks)
