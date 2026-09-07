# api/schemas/person.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class PersonBase(BaseModel):
    """Base person schema."""
    global_id: str = Field(..., description="Global person identifier")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PersonCreate(PersonBase):
    """Person creation schema."""
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class PersonUpdate(BaseModel):
    """Person update schema."""
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
    last_seen: Optional[datetime] = None

class PersonResponse(PersonBase):
    """Person response schema."""
    first_seen: datetime
    last_seen: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PersonListResponse(BaseModel):
    """Person list response."""
    items: List[PersonResponse]
    total: int
    page: int = 1
    per_page: int = 20

# Biometric Profile Schemas
class BiometricProfileBase(BaseModel):
    """Base biometric profile schema."""
    global_id: str
    face_quality: float = Field(0.0, ge=0.0, le=1.0)
    reid_quality: float = Field(0.0, ge=0.0, le=1.0)

class BiometricProfileResponse(BiometricProfileBase):
    """Biometric profile response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Timeline Schemas
class TimelineEvent(BaseModel):
    """Timeline event schema."""
    timestamp: datetime
    camera_id: int
    event_type: str
    duration: Optional[float] = None
    confidence: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PersonTimelineResponse(BaseModel):
    """Person timeline response."""
    global_id: str
    events: List[TimelineEvent]
    cameras_visited: List[int]
    total_duration: float
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None