# api/schemas/search.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"

class ComparisonOperator(str, Enum):
    """Comparison operators."""
    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    BETWEEN = "between"
    IN = "in"
    CONTAINS = "contains"

class TimeRange(BaseModel):
    """Time range for search."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None

class SpatialFilter(BaseModel):
    """Spatial filter for search."""
    cameras: List[int] = Field(default_factory=list)
    min_dwell_time: Optional[float] = None
    max_dwell_time: Optional[float] = None
    from_cameras: Optional[List[int]] = None
    to_cameras: Optional[List[int]] = None

class PersonFilter(BaseModel):
    """Person filter for search."""
    global_ids: List[str] = Field(default_factory=list)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    face_available: Optional[bool] = None
    reid_available: Optional[bool] = None

class EventFilter(BaseModel):
    """Event filter for search."""
    event_types: List[str] = Field(default_factory=list)
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None

class SearchQuery(BaseModel):
    """Search query schema."""
    time_range: Optional[TimeRange] = None
    spatial: SpatialFilter = Field(default_factory=SpatialFilter)
    person: PersonFilter = Field(default_factory=PersonFilter)
    event: EventFilter = Field(default_factory=EventFilter)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    sort_by: str = "timestamp"
    sort_order: SortOrder = SortOrder.DESC
    limit: int = Field(100, gt=0, le=1000)
    offset: int = Field(0, ge=0)

class SearchResponse(BaseModel):
    """Search response schema."""
    results: List[Dict[str, Any]]
    aggregated: Dict[str, Any]
    result_type: str
    total_count: int
    query: Dict[str, Any]
    timestamp: datetime

class TextSearchRequest(BaseModel):
    """Text search request."""
    text: str = Field(..., description="Natural language search query")
    limit: Optional[int] = Field(100, gt=0, le=1000)