# api/routes/search.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from datetime import datetime

from ..schemas.search import (
    SearchQuery, SearchResponse, TextSearchRequest
)
from ..schemas.response import ResponseModel
from ..dependencies.database import get_search_engine
from search.query_engine import QueryEngine
from search.query_builder import QueryBuilder

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(
    query: SearchQuery,
    search_engine: QueryEngine = Depends(get_search_engine)
):
    """
    Execute a structured search.
    
    Args:
        query: Search query
    
    Returns:
        Search results
    """
    try:
        # Convert Pydantic model to QueryEngine query
        query_dict = query.dict(exclude_none=True)
        
        # Execute search
        results = search_engine.search(query_dict)
        
        return SearchResponse(
            results=results['results'],
            aggregated=results['aggregated'],
            result_type=results['result_type'],
            total_count=results['total_count'],
            query=results['query'],
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/search/text", response_model=SearchResponse)
async def text_search(
    request: TextSearchRequest,
    search_engine: QueryEngine = Depends(get_search_engine)
):
    """
    Natural language text search.
    
    Args:
        request: Text search request
    
    Returns:
        Search results
    """
    try:
        results = search_engine.search_by_text(request.text)
        
        # Apply limit
        if request.limit:
            results['results'] = results['results'][:request.limit]
            results['total_count'] = len(results['results'])
        
        return SearchResponse(
            results=results['results'],
            aggregated=results.get('aggregated', {}),
            result_type=results.get('result_type', 'unknown'),
            total_count=results['total_count'],
            query=results.get('query', {}),
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/search/persons", response_model=ResponseModel)
async def search_persons(
    global_id: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_confidence: Optional[float] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine)
):
    """
    Quick person search.
    
    Args:
        global_id: Person ID filter
        camera_id: Camera ID filter
        start_time: Start time
        end_time: End time
        min_confidence: Minimum confidence
        limit: Results limit
    
    Returns:
        Person search results
    """
    builder = QueryBuilder()
    
    if start_time or end_time:
        builder = builder.with_time_range(start_time, end_time)
    
    if camera_id is not None:
        builder = builder.with_cameras([camera_id])
    
    if global_id:
        builder = builder.with_person([global_id])
    
    if min_confidence is not None:
        builder = builder.with_confidence(min_confidence)
    
    builder = builder.limit(limit)
    
    query = builder.build()
    results = search_engine.search(query.to_dict())
    
    return ResponseModel(
        success=True,
        data=results
    )

@router.get("/search/events", response_model=ResponseModel)
async def search_events(
    event_type: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine)
):
    """
    Search events.
    
    Args:
        event_type: Event type filter
        camera_id: Camera ID filter
        start_time: Start time
        end_time: End time
        limit: Results limit
    
    Returns:
        Event search results
    """
    builder = QueryBuilder()
    
    if start_time or end_time:
        builder = builder.with_time_range(start_time, end_time)
    
    if camera_id is not None:
        builder = builder.with_cameras([camera_id])
    
    if event_type:
        builder = builder.with_event_types([event_type])
    
    builder = builder.limit(limit)
    
    query = builder.build()
    results = search_engine.search(query.to_dict())
    
    return ResponseModel(
        success=True,
        data=results
    )

@router.get("/search/transitions", response_model=ResponseModel)
async def search_transitions(
    from_camera: Optional[int] = None,
    to_camera: Optional[int] = None,
    global_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    search_engine: QueryEngine = Depends(get_search_engine)
):
    """
    Search camera transitions.
    
    Args:
        from_camera: Source camera
        to_camera: Destination camera
        global_id: Person ID filter
        start_time: Start time
        end_time: End time
        limit: Results limit
    
    Returns:
        Transition search results
    """
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
    
    query = builder.build()
    results = search_engine.search(query.to_dict())
    
    return ResponseModel(
        success=True,
        data=results
    )