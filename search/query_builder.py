# search/query_builder.py
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

class SortOrder(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

class ComparisonOperator(Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    BETWEEN = "between"
    IN = "in"
    CONTAINS = "contains"

@dataclass
class FilterCondition:
    """A single filter condition."""
    field: str
    operator: ComparisonOperator
    value: Any
    value2: Optional[Any] = None  # For BETWEEN operator

@dataclass
class TimeRange:
    """Time range for queries."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    def is_active(self) -> bool:
        return self.start is not None or self.end is not None

@dataclass
class SpatialFilter:
    """Spatial filter for queries."""
    cameras: List[int] = field(default_factory=list)
    camera_operators: List[str] = field(default_factory=list)  # AND, OR
    min_dwell_time: Optional[float] = None
    max_dwell_time: Optional[float] = None
    transition_filter: Optional[Dict] = None  # {from: [cameras], to: [cameras]}

@dataclass
class PersonFilter:
    """Person-specific filters."""
    global_ids: List[str] = field(default_factory=list)
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    face_available: Optional[bool] = None
    reid_available: Optional[bool] = None

@dataclass
class EventFilter:
    """Event-specific filters."""
    event_types: List[str] = field(default_factory=list)
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None

@dataclass
class SearchQuery:
    """Complete search query."""
    time_range: TimeRange = field(default_factory=TimeRange)
    spatial: SpatialFilter = field(default_factory=SpatialFilter)
    person: PersonFilter = field(default_factory=PersonFilter)
    event: EventFilter = field(default_factory=EventFilter)
    conditions: List[FilterCondition] = field(default_factory=list)
    sort_by: str = "timestamp"
    sort_order: SortOrder = SortOrder.DESCENDING
    limit: int = 100
    offset: int = 0
    
    def to_dict(self) -> Dict:
        """Convert query to dictionary."""
        return {
            'time_range': {
                'start': self.time_range.start.isoformat() if self.time_range.start else None,
                'end': self.time_range.end.isoformat() if self.time_range.end else None
            },
            'spatial': {
                'cameras': self.spatial.cameras,
                'min_dwell_time': self.spatial.min_dwell_time,
                'max_dwell_time': self.spatial.max_dwell_time,
                'transition_filter': self.spatial.transition_filter
            },
            'person': {
                'global_ids': self.person.global_ids,
                'min_confidence': self.person.min_confidence,
                'max_confidence': self.person.max_confidence,
                'face_available': self.person.face_available,
                'reid_available': self.person.reid_available
            },
            'event': {
                'event_types': self.event.event_types,
                'min_duration': self.event.min_duration,
                'max_duration': self.event.max_duration
            },
            'sort_by': self.sort_by,
            'sort_order': self.sort_order.value,
            'limit': self.limit,
            'offset': self.offset
        }

class QueryBuilder:
    """
    Builder for creating structured search queries.
    """
    
    def __init__(self):
        self.query = SearchQuery()
    
    def with_time_range(self, start: Optional[datetime] = None,
                        end: Optional[datetime] = None) -> 'QueryBuilder':
        """Set time range."""
        self.query.time_range = TimeRange(start=start, end=end)
        return self
    
    def with_last_hours(self, hours: int) -> 'QueryBuilder':
        """Set time range to last N hours."""
        now = datetime.now()
        self.query.time_range = TimeRange(
            start=now - timedelta(hours=hours),
            end=now
        )
        return self
    
    def with_last_days(self, days: int) -> 'QueryBuilder':
        """Set time range to last N days."""
        now = datetime.now()
        self.query.time_range = TimeRange(
            start=now - timedelta(days=days),
            end=now
        )
        return self
    
    def with_cameras(self, cameras: List[int], 
                     operator: str = "OR") -> 'QueryBuilder':
        """Filter by cameras."""
        self.query.spatial.cameras = cameras
        self.query.spatial.camera_operators = [operator] * len(cameras)
        return self
    
    def with_dwell_time(self, min_time: Optional[float] = None,
                        max_time: Optional[float] = None) -> 'QueryBuilder':
        """Filter by dwell time."""
        self.query.spatial.min_dwell_time = min_time
        self.query.spatial.max_dwell_time = max_time
        return self
    
    def with_transition(self, from_cameras: List[int],
                       to_cameras: List[int]) -> 'QueryBuilder':
        """Filter by camera transitions."""
        self.query.spatial.transition_filter = {
            'from': from_cameras,
            'to': to_cameras
        }
        return self
    
    def with_person(self, global_ids: List[str]) -> 'QueryBuilder':
        """Filter by person IDs."""
        self.query.person.global_ids = global_ids
        return self
    
    def with_confidence(self, min_conf: float, 
                        max_conf: Optional[float] = None) -> 'QueryBuilder':
        """Filter by confidence score."""
        self.query.person.min_confidence = min_conf
        self.query.person.max_confidence = max_conf
        return self
    
    def with_face_available(self, available: bool = True) -> 'QueryBuilder':
        """Filter by face availability."""
        self.query.person.face_available = available
        return self
    
    def with_event_types(self, event_types: List[str]) -> 'QueryBuilder':
        """Filter by event types."""
        self.query.event.event_types = event_types
        return self
    
    def with_event_duration(self, min_time: Optional[float] = None,
                           max_time: Optional[float] = None) -> 'QueryBuilder':
        """Filter by event duration."""
        self.query.event.min_duration = min_time
        self.query.event.max_duration = max_time
        return self
    
    def sort_by(self, field: str, 
                order: SortOrder = SortOrder.DESCENDING) -> 'QueryBuilder':
        """Set sort field and order."""
        self.query.sort_by = field
        self.query.sort_order = order
        return self
    
    def limit(self, limit: int, offset: int = 0) -> 'QueryBuilder':
        """Set limit and offset."""
        self.query.limit = limit
        self.query.offset = offset
        return self
    
    def add_condition(self, field: str, operator: ComparisonOperator,
                     value: Any, value2: Optional[Any] = None) -> 'QueryBuilder':
        """Add a custom condition."""
        self.query.conditions.append(
            FilterCondition(field, operator, value, value2)
        )
        return self
    
    def build(self) -> SearchQuery:
        """Build and return the search query."""
        return self.query