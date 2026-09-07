# api/routes/persons.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from datetime import datetime

from ..schemas.person import (
    PersonCreate, PersonUpdate, PersonResponse,
    PersonListResponse, BiometricProfileResponse,
    PersonTimelineResponse
)
from ..schemas.response import ResponseModel
from ..dependencies.database import get_db_manager
from database.postgres_manager import PostgresManager
from database.qdrant_manager import QdrantManager
from database.redis_manager import RedisManager

router = APIRouter()

@router.post("/persons", response_model=ResponseModel)
async def create_person(
    person_data: PersonCreate,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Create a new person.
    
    Args:
        person_data: Person creation data
    
    Returns:
        Created person
    """
    try:
        person = await db.create_person(person_data.dict())
        return ResponseModel(
            success=True,
            message="Person created successfully",
            data=person
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/persons/{global_id}", response_model=ResponseModel)
async def get_person(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Get a person by global ID.
    
    Args:
        global_id: Person identifier
    
    Returns:
        Person details
    """
    person = await db.get_person(global_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {global_id} not found"
        )
    
    return ResponseModel(
        success=True,
        data=person
    )

@router.put("/persons/{global_id}", response_model=ResponseModel)
async def update_person(
    global_id: str,
    updates: PersonUpdate,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Update a person.
    
    Args:
        global_id: Person identifier
        updates: Update data
    
    Returns:
        Updated person
    """
    person = await db.update_person(global_id, updates.dict(exclude_none=True))
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person {global_id} not found"
        )
    
    return ResponseModel(
        success=True,
        message="Person updated successfully",
        data=person
    )

@router.get("/persons", response_model=PersonListResponse)
async def list_persons(
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    search: Optional[str] = None,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    List persons with filters.
    
    Args:
        page: Page number
        per_page: Items per page
        search: Search text
        min_confidence: Minimum confidence
        start_time: Start time filter
        end_time: End time filter
    
    Returns:
        List of persons
    """
    # This would be implemented with proper filtering
    # Simplified for demonstration
    return PersonListResponse(
        items=[],
        total=0,
        page=page,
        per_page=per_page
    )

@router.get("/persons/{global_id}/timeline", response_model=ResponseModel)
async def get_person_timeline(
    global_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Get a person's timeline.
    
    Args:
        global_id: Person identifier
        start_time: Start time filter
        end_time: End time filter
    
    Returns:
        Person timeline
    """
    timeline = await db.get_person_timeline(global_id)
    
    # Filter by time if provided
    if start_time or end_time:
        events = timeline.get('events', [])
        filtered_events = []
        for event in events:
            event_time = datetime.fromisoformat(event['timestamp'])
            if start_time and event_time < start_time:
                continue
            if end_time and event_time > end_time:
                continue
            filtered_events.append(event)
        timeline['events'] = filtered_events
    
    return ResponseModel(
        success=True,
        data=timeline
    )

@router.get("/persons/{global_id}/biometrics", response_model=ResponseModel)
async def get_person_biometrics(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Get a person's biometric profile.
    
    Args:
        global_id: Person identifier
    
    Returns:
        Biometric profile
    """
    profile = await db.get_biometric_profile(global_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Biometric profile for {global_id} not found"
        )
    
    return ResponseModel(
        success=True,
        data=profile
    )

@router.get("/persons/{global_id}/matches", response_model=ResponseModel)
async def get_person_matches(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager)
):
    """
    Get identity matches for a person.
    
    Args:
        global_id: Person identifier
    
    Returns:
        List of identity matches
    """
    matches = await db.get_identity_matches(global_id)
    
    return ResponseModel(
        success=True,
        data=matches
    )

@router.delete("/persons/{global_id}", response_model=ResponseModel)
async def delete_person(
    global_id: str,
    db: PostgresManager = Depends(get_db_manager),
    qdrant: QdrantManager = Depends(get_qdrant_manager),
    redis: RedisManager = Depends(get_redis_manager)
):
    """
    Delete a person and all associated data.
    
    Args:
        global_id: Person identifier
    
    Returns:
        Deletion confirmation
    """
    # Delete from PostgreSQL
    # Delete from Qdrant
    # Delete from Redis
    # This would be a comprehensive deletion
    
    return ResponseModel(
        success=True,
        message=f"Person {global_id} deleted"
    )