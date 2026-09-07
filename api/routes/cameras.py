# api/routes/cameras.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from api.schemas.response import ResponseModel
from api.dependencies.database import get_db_manager, get_redis_manager, get_identity_store
from api.dependencies.auth import get_current_user, require_roles, Role, UserPublic
from database.postgres_manager import PostgresManager
from database.redis_manager import RedisManager
from database.identity_store import IdentityStore

router = APIRouter()


@router.get("/cameras", response_model=ResponseModel)
async def list_cameras(
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    """List cameras from PostgreSQL when available; else SQLite-derived IDs."""
    from api.dependencies.database import get_managers_raw, dependency_status

    status_map = dependency_status()
    managers = get_managers_raw()
    db = managers.get("postgres")
    if status_map.get("postgresql") == "ok" and db is not None:
        try:
            cameras = await db.get_all_cameras()
            if cameras:
                return ResponseModel(success=True, data=cameras)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PostgreSQL camera list failed: {exc}") from exc

    derived = []
    try:
        persons = store.get_all()
        cam_ids = set()
        for p in persons:
            cid = p.get("last_camera") or p.get("last_camera_id") or p.get("camera_id")
            if cid is not None:
                cam_ids.add(cid)
        for cid in sorted(cam_ids, key=str):
            derived.append(
                {
                    "camera_id": cid,
                    "name": f"Camera {cid}",
                    "location": None,
                    "capacity": 100,
                    "metadata": {"source": "sqlite_derived"},
                }
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list cameras: {exc}") from exc

    return ResponseModel(success=True, data=derived)


@router.post("/cameras", response_model=ResponseModel)
async def create_camera(
    camera_data: CameraCreate,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
):
    try:
        camera = await db.create_camera(camera_data.model_dump())
        return ResponseModel(success=True, message="Camera created", data=camera)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/cameras/{camera_id}", response_model=ResponseModel)
async def get_camera(
    camera_id: int,
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    camera = await db.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return ResponseModel(success=True, data=camera)


@router.get("/cameras/{camera_id}/status", response_model=ResponseModel)
async def camera_status(
    camera_id: int,
    redis: RedisManager = Depends(get_redis_manager),
    _: UserPublic = Depends(get_current_user),
):
    state = await redis.get_camera_state(camera_id)
    if not state:
        return ResponseModel(
            success=True,
            data={
                "camera_id": camera_id,
                "status": "unknown",
                "message": "No live state in Redis",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )
    return ResponseModel(success=True, data=state)


@router.get("/cameras/topology/graph", response_model=ResponseModel)
async def camera_topology(
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    """Return camera topology from CameraGraph (SQLite-backed). Does not invent edges."""
    try:
        from topology.camera_graph import CameraGraph

        graph = CameraGraph(db_path=store.db_path)
        edges = []
        for (frm, to), transition in graph.transitions.items():
            edges.append(
                {
                    "from_camera": frm,
                    "to_camera": to,
                    "label": f"CAM{frm:02d} → CAM{to:02d}" if isinstance(frm, int) else f"{frm} → {to}",
                    **transition.to_dict(),
                }
            )
        nodes = list(graph.graph.nodes())
        return ResponseModel(
            success=True,
            data={"nodes": nodes, "edges": edges, "edge_count": len(edges)},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Topology unavailable: {exc}") from exc


@router.get("/cameras/{camera_id}/stats", response_model=ResponseModel)
async def camera_stats(
    camera_id: int,
    hours: int = Query(24, gt=0, le=168),
    db: PostgresManager = Depends(get_db_manager),
    _: UserPublic = Depends(get_current_user),
):
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    stats = await db.get_camera_statistics(camera_id, start, end)
    return ResponseModel(success=True, data=stats)
