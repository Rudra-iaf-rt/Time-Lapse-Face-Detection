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
from camera.manager import test_camera_source
from camera.runtime import camera_runtime

router = APIRouter()
@router.get("/cameras/runtimes", response_model=ResponseModel)
async def list_camera_runtime(_: UserPublic = Depends(get_current_user)):
    return ResponseModel(success=True, data=camera_runtime.list_statuses())




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
        payload = camera_data.model_dump()
        payload["metadata"] = {
            **(payload.get("metadata") or {}),
            "source_type": payload.get("source_type"),
            "source_uri": payload.get("source_uri"),
            "fps_target": payload.get("fps_target"),
            "frame_skip": payload.get("frame_skip"),
            "roi": payload.get("roi"),
        }
        camera = await db.create_camera(payload)
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


class CameraSourceTestRequest:
    pass


from pydantic import BaseModel


class CameraTestBody(BaseModel):
    source_uri: str
    sample_frames: int = 5


class CameraRunBody(BaseModel):
    source_uri: Optional[str] = None
    source_type: Optional[str] = None
    roi: Optional[List[int]] = None


@router.post("/cameras/test", response_model=ResponseModel)
async def test_camera(
    body: CameraTestBody,
    _: UserPublic = Depends(get_current_user),
):
    result = test_camera_source(body.source_uri, body.sample_frames)
    return ResponseModel(
        success=result.get("ok", False),
        data=result,
        message="Camera source test complete",
    )
@router.post("/cameras/{camera_id}/start", response_model=ResponseModel)
async def start_camera(
    camera_id: int,
    body: Optional[CameraRunBody] = None,
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    from api.dependencies.database import get_managers_raw, dependency_status

    managers = get_managers_raw()
    status_map = dependency_status()
    source_uri = body.source_uri if body else None
    roi = body.roi if body else None
    db = managers.get("postgres")

    if source_uri is None and status_map.get("postgresql") == "ok" and db is not None:
        try:
            camera = await db.get_camera(camera_id)
            if camera:
                meta = camera.get("camera_metadata") or camera.get("metadata") or {}
                source_uri = meta.get("source_uri") or camera.get("source_uri")
                roi = roi if roi is not None else meta.get("roi")
        except Exception:
            source_uri = None

    if roi is None and body is not None:
        roi = body.roi

    if not source_uri:
        raise HTTPException(status_code=400, detail="source_uri is required or camera must be registered with a source")

    status = camera_runtime.start(camera_id, source_uri, roi=roi)
    return ResponseModel(success=True, message="Camera runtime started", data=status)


@router.post("/cameras/{camera_id}/stop", response_model=ResponseModel)
async def stop_camera(
    camera_id: int,
    _: UserPublic = Depends(get_current_user),
):
    status = camera_runtime.stop(camera_id)
    return ResponseModel(success=True, message="Camera runtime stopped", data=status)


@router.get("/cameras/{camera_id}/runtime", response_model=ResponseModel)
async def get_camera_runtime(
    camera_id: int,
    _: UserPublic = Depends(get_current_user),
):
    return ResponseModel(success=True, data=camera_runtime.get_status(camera_id))
