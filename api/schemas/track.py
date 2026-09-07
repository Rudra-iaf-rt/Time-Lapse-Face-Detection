# api/schemas/track.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class TrackBase(BaseModel):
    """Base track schema — local track, not permanent identity."""

    track_id: str = Field(..., description="Local track ID, e.g. CAM01-T17")
    global_id: Optional[str] = Field(None, description="Canonical global identity PERSON_XXXX")
    camera_id: int
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class TrackCreate(TrackBase):
    """Track creation schema."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrackUpdate(BaseModel):
    """Track update schema."""

    global_id: Optional[str] = None
    end_time: Optional[datetime] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class TrackResponse(TrackBase):
    """Track response schema."""

    id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ObservationResponse(BaseModel):
    """Single observation / sighting."""

    id: Optional[int] = None
    track_id: str
    global_id: Optional[str] = None
    camera_id: int
    timestamp: datetime
    bbox: List[float] = Field(default_factory=list)
    confidence: float = 0.5
    quality: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrackListResponse(BaseModel):
    """Paginated tracks."""

    items: List[TrackResponse]
    total: int
    page: int = 1
    per_page: int = 20
