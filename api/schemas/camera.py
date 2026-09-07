# api/schemas/camera.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class CameraBase(BaseModel):
    """Base camera schema."""
    camera_id: int = Field(..., description="Camera identifier")
    name: str = Field(..., description="Camera name")
    location: Optional[str] = Field(None, description="Camera location")
    capacity: int = Field(100, gt=0, description="Camera capacity")

class CameraCreate(CameraBase):
    """Camera creation schema."""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CameraUpdate(BaseModel):
    """Camera update schema."""
    name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    metadata: Optional[Dict[str, Any]] = None

class CameraResponse(CameraBase):
    """Camera response schema."""
    id: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True

class CameraStateResponse(BaseModel):
    """Camera state response."""
    camera_id: int
    occupancy: int
    capacity: int
    utilization: float
    congestion_level: str
    active_tracks: List[str]
    timestamp: datetime

class CameraStatistics(BaseModel):
    """Camera statistics."""
    camera_id: int
    observation_count: int
    unique_persons: int
    avg_confidence: float
    start_time: datetime
    end_time: datetime