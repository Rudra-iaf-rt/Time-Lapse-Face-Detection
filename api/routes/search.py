# api/routes/search.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.search import SearchQuery, SearchResponse, TextSearchRequest
from api.schemas.response import ResponseModel
from api.dependencies.database import get_search_engine, get_identity_store
from api.dependencies.auth import get_current_user, UserPublic
from search.query_engine import QueryEngine
from search.query_builder import QueryBuilder
from database.identity_store import IdentityStore

router = APIRouter()


def _to_engine_query(query: SearchQuery):
    """Convert API Pydantic SearchQuery into search.query_builder query object."""
    builder = QueryBuilder()

    if query.time_range:
        builder = builder.with_time_range(query.time_range.start, query.time_range.end)

    if query.spatial and query.spatial.cameras:
        builder = builder.with_cameras(query.spatial.cameras)

    if query.spatial and query.spatial.from_cameras is not None and query.spatial.to_cameras is not None:
        builder = builder.with_transition(query.spatial.from_cameras, query.spatial.to_cameras)

    if query.person and query.person.global_ids:
        builder = builder.with_person(query.person.global_ids)

    if query.person and query.person.min_confidence is not None:
        builder = builder.with_confidence(query.person.min_confidence)

    if query.event and query.event.event_types:
        builder = builder.with_event_types(query.event.event_types)

    builder = builder.limit(query.limit)
    return builder.build()


@router.post("/search", response_model=SearchResponse)
async def search(
    query: SearchQuery,
    search_engine: QueryEngine = Depends(get_search_engine),
    _: UserPublic = Depends(get_current_user),
):
    try:
        engine_query = _to_engine_query(query)
        results = search_engine.search(engine_query)
        return SearchResponse(
            results=results["results"],
            aggregated=results.get("aggregated", {}),
            result_type=results.get("result_type", "unknown"),
            total_count=results["total_count"],
            query=results.get("query", {}),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/search/text", response_model=SearchResponse)
async def text_search(
    request: TextSearchRequest,
    search_engine: QueryEngine = Depends(get_search_engine),
    _: UserPublic = Depends(get_current_user),
):
    try:
        results = search_engine.search_by_text(request.text)
        if request.limit:
            results["results"] = results["results"][: request.limit]
            results["total_count"] = len(results["results"])
        return SearchResponse(
            results=results["results"],
            aggregated=results.get("aggregated", {}),
            result_type=results.get("result_type", "unknown"),
            total_count=results["total_count"],
            query=results.get("query", {}),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/search/persons", response_model=ResponseModel)
async def search_persons(
    global_id: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine),
    store: IdentityStore = Depends(get_identity_store),
    _: UserPublic = Depends(get_current_user),
):
    if global_id and not camera_id and not start_time and not end_time:
        person = store.get_person(global_id)
        return ResponseModel(
            success=True,
            data={"results": [person] if person else [], "total_count": 1 if person else 0},
        )

    if start_time or end_time or camera_id is not None:
        try:
            rows = store.search_by_time(
                since=start_time.timestamp() if start_time else None,
                until=end_time.timestamp() if end_time else None,
                camera_id=camera_id,
            )
            if global_id:
                rows = [r for r in rows if r.get("global_id") == global_id]
            if min_confidence is not None:
                rows = [
                    r
                    for r in rows
                    if (r.get("confidence") or r.get("match_score") or 0) >= min_confidence
                ]
            return ResponseModel(
                success=True,
                data={"results": rows[:limit], "total_count": len(rows[:limit]), "source": "identity_store"},
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Default: list from IdentityStore (avoid fragile QueryEngine path for empty filters)
    try:
        rows = store.get_all()
        if global_id:
            rows = [r for r in rows if r.get("global_id") == global_id]
        return ResponseModel(
            success=True,
            data={"results": rows[:limit], "total_count": len(rows[:limit]), "source": "identity_store"},
        )
    except Exception:
        builder = QueryBuilder()
        if min_confidence is not None:
            builder = builder.with_confidence(min_confidence)
        builder = builder.limit(limit)
        results = search_engine.search(builder.build())
        return ResponseModel(success=True, data=results)


@router.get("/search/events", response_model=ResponseModel)
async def search_events(
    event_type: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine),
    _: UserPublic = Depends(get_current_user),
):
    builder = QueryBuilder()
    if start_time or end_time:
        builder = builder.with_time_range(start_time, end_time)
    if camera_id is not None:
        builder = builder.with_cameras([camera_id])
    if event_type:
        builder = builder.with_event_types([event_type])
    builder = builder.limit(limit)
    results = search_engine.search(builder.build())
    return ResponseModel(success=True, data=results)


@router.get("/search/transitions", response_model=ResponseModel)
async def search_transitions(
    from_camera: Optional[int] = None,
    to_camera: Optional[int] = None,
    global_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine),
    _: UserPublic = Depends(get_current_user),
):
    builder = QueryBuilder()
    if start_time or end_time:
        builder = builder.with_time_range(start_time, end_time)
    if from_camera is not None and to_camera is not None:
        builder = builder.with_transition([from_camera], [to_camera])
    elif from_camera is not None:
        builder = builder.with_transition([from_camera], [])
    elif to_camera is not None:
        builder = builder.with_transition([], [to_camera])
    if global_id:
        builder = builder.with_person([global_id])
    builder = builder.limit(limit)
    results = search_engine.search(builder.build())
    return ResponseModel(success=True, data=results)
