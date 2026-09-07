# timeline/timeline_builder.py
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

@dataclass
class TimelineEvent:
    """A single event in a person's timeline."""
    event_type: str  # 'entry', 'exit', 'movement', 'dwell', 'appearance'
    camera_id: int
    timestamp: datetime
    duration: Optional[float] = None
    location: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class TimelineSegment:
    """A continuous segment in a person's timeline."""
    camera_id: int
    start_time: datetime
    end_time: datetime
    duration: float
    events: List[TimelineEvent] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

@dataclass
class PersonTimeline:
    """Complete timeline for a person."""
    global_id: str
    segments: List[TimelineSegment] = field(default_factory=list)
    events: List[TimelineEvent] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_duration: float = 0.0
    cameras_visited: List[int] = field(default_factory=list)
    route: List[int] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def add_segment(self, segment: TimelineSegment):
        """Add a segment to the timeline."""
        self.segments.append(segment)
        
        # Update metadata
        if self.first_seen is None or segment.start_time < self.first_seen:
            self.first_seen = segment.start_time
        if self.last_seen is None or segment.end_time > self.last_seen:
            self.last_seen = segment.end_time
            
        if segment.camera_id not in self.cameras_visited:
            self.cameras_visited.append(segment.camera_id)
        
        # Update total duration
        self.total_duration += segment.duration
        
        # Update route
        if self.route and self.route[-1] != segment.camera_id:
            self.route.append(segment.camera_id)
        elif not self.route:
            self.route.append(segment.camera_id)
    
    def get_segments_in_time_range(self, start: datetime, 
                                   end: datetime) -> List[TimelineSegment]:
        """Get segments within a time range."""
        return [
            seg for seg in self.segments
            if seg.start_time >= start and seg.end_time <= end
        ]
    
    def get_camera_dwell_times(self) -> Dict[int, float]:
        """Get total dwell time per camera."""
        dwell_times = defaultdict(float)
        for segment in self.segments:
            dwell_times[segment.camera_id] += segment.duration
        return dict(dwell_times)
    
    def get_timeline_summary(self) -> Dict:
        """Get a summary of the timeline."""
        return {
            'global_id': self.global_id,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'total_duration': self.total_duration,
            'segments_count': len(self.segments),
            'cameras_visited': self.cameras_visited,
            'route': self.route,
            'camera_dwell_times': self.get_camera_dwell_times()
        }
    
    def to_dict(self) -> Dict:
        """Convert timeline to dictionary."""
        return {
            'global_id': self.global_id,
            'segments': [
                {
                    'camera_id': seg.camera_id,
                    'start_time': seg.start_time.isoformat(),
                    'end_time': seg.end_time.isoformat(),
                    'duration': seg.duration,
                    'confidence': seg.confidence,
                    'events': [
                        {
                            'event_type': ev.event_type,
                            'camera_id': ev.camera_id,
                            'timestamp': ev.timestamp.isoformat(),
                            'duration': ev.duration,
                            'confidence': ev.confidence
                        }
                        for ev in seg.events
                    ],
                    'metadata': seg.metadata
                }
                for seg in self.segments
            ],
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'total_duration': self.total_duration,
            'cameras_visited': self.cameras_visited,
            'route': self.route,
            'metadata': self.metadata
        }

class TimelineBuilder:
    """
    Build person-centric timelines from tracking data.
    """
    
    def __init__(self, db_path: str = "database/identities.db",
                 min_segment_duration: float = 1.0,
                 max_gap_duration: float = 60.0):
        """
        Initialize timeline builder.
        
        Args:
            db_path: Path to database
            min_segment_duration: Minimum duration for a segment (seconds)
            max_gap_duration: Maximum gap to consider continuous (seconds)
        """
        self.db_path = db_path
        self.min_segment_duration = min_segment_duration
        self.max_gap_duration = max_gap_duration
        self.timelines: Dict[str, PersonTimeline] = {}
        
    def build_timelines(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> Dict[str, PersonTimeline]:
        """
        Build timelines for all persons in the database.
        
        Returns:
            Dictionary of global_id -> PersonTimeline
        """
        # Get all observations grouped by global ID
        observations = self._get_observations(start_time, end_time)
        
        # Build timeline for each person
        for global_id, obs_list in observations.items():
            timeline = self._build_person_timeline(global_id, obs_list)
            self.timelines[global_id] = timeline
            
        return self.timelines
    
    def _get_observations(self, start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """Get observations from database grouped by global ID."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = '''
            SELECT 
                global_id,
                camera_id,
                track_id,
                timestamp,
                quality
            FROM reid_profiles
            WHERE global_id IS NOT NULL
        '''
        
        params = []
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())
        
        query += ' ORDER BY global_id, timestamp'
        
        cursor.execute(query, params)
        
        observations = defaultdict(list)
        for row in cursor.fetchall():
            global_id, camera_id, track_id, timestamp_str, quality = row
            observations[global_id].append({
                'camera_id': camera_id,
                'track_id': track_id,
                'timestamp': datetime.fromisoformat(timestamp_str),
                'quality': quality or 0.5
            })
        
        conn.close()
        return observations
    
    def _build_person_timeline(self, global_id: str,
                               observations: List[Dict]) -> PersonTimeline:
        """Build timeline for a single person."""
        if not observations:
            return PersonTimeline(global_id=global_id)
        
        # Sort observations by timestamp
        sorted_obs = sorted(observations, key=lambda x: x['timestamp'])
        
        # Create timeline
        timeline = PersonTimeline(global_id=global_id)
        
        # Group observations into segments
        segments = self._group_into_segments(sorted_obs)
        
        # Add segments to timeline
        for segment_data in segments:
            segment = TimelineSegment(
                camera_id=segment_data['camera_id'],
                start_time=segment_data['start_time'],
                end_time=segment_data['end_time'],
                duration=segment_data['duration'],
                confidence=segment_data['confidence'],
                events=self._create_events(segment_data)
            )
            timeline.add_segment(segment)
        
        # Detect events
        timeline.events = self._detect_events(timeline)
        
        return timeline
    
    def _group_into_segments(self, observations: List[Dict]) -> List[Dict]:
        """Group observations into continuous segments."""
        if not observations:
            return []
        
        segments = []
        current_segment = {
            'camera_id': observations[0]['camera_id'],
            'start_time': observations[0]['timestamp'],
            'end_time': observations[0]['timestamp'],
            'observations': [observations[0]],
            'confidence': observations[0]['quality']
        }
        
        for obs in observations[1:]:
            time_gap = (obs['timestamp'] - current_segment['end_time']).total_seconds()
            
            # Check if same camera and small gap
            if (obs['camera_id'] == current_segment['camera_id'] and 
                time_gap <= self.max_gap_duration):
                # Extend current segment
                current_segment['end_time'] = obs['timestamp']
                current_segment['observations'].append(obs)
                current_segment['confidence'] = max(
                    current_segment['confidence'],
                    obs['quality']
                )
            else:
                # Finalize current segment
                if len(current_segment['observations']) >= 2:
                    current_segment['duration'] = (
                        current_segment['end_time'] - current_segment['start_time']
                    ).total_seconds()
                    segments.append(current_segment)
                
                # Start new segment
                current_segment = {
                    'camera_id': obs['camera_id'],
                    'start_time': obs['timestamp'],
                    'end_time': obs['timestamp'],
                    'observations': [obs],
                    'confidence': obs['quality']
                }
        
        # Add last segment
        if len(current_segment['observations']) >= 2:
            current_segment['duration'] = (
                current_segment['end_time'] - current_segment['start_time']
            ).total_seconds()
            segments.append(current_segment)
        
        return segments
    
    def _create_events(self, segment_data: Dict) -> List[TimelineEvent]:
        """Create events from segment data."""
        events = []
        observations = segment_data['observations']
        
        if len(observations) >= 2:
            # Entry event
            events.append(TimelineEvent(
                event_type='entry',
                camera_id=segment_data['camera_id'],
                timestamp=observations[0]['timestamp'],
                confidence=observations[0]['quality']
            ))
            
            # Dwell event
            events.append(TimelineEvent(
                event_type='dwell',
                camera_id=segment_data['camera_id'],
                timestamp=segment_data['start_time'],
                duration=segment_data['duration'],
                confidence=segment_data['confidence']
            ))
            
            # Exit event
            events.append(TimelineEvent(
                event_type='exit',
                camera_id=segment_data['camera_id'],
                timestamp=observations[-1]['timestamp'],
                confidence=observations[-1]['quality']
            ))
        
        return events
    
    def _detect_events(self, timeline: PersonTimeline) -> List[TimelineEvent]:
        """Detect events from timeline segments."""
        events = []
        
        # Collect all events from segments
        for segment in timeline.segments:
            events.extend(segment.events)
        
        # Add transition events between segments
        for i in range(len(timeline.segments) - 1):
            current = timeline.segments[i]
            next_seg = timeline.segments[i + 1]
            
            if current.camera_id != next_seg.camera_id:
                # Movement event
                events.append(TimelineEvent(
                    event_type='movement',
                    camera_id=current.camera_id,
                    timestamp=current.end_time,
                    duration=(next_seg.start_time - current.end_time).total_seconds(),
                    confidence=min(current.confidence, next_seg.confidence),
                    metadata={
                        'from_camera': current.camera_id,
                        'to_camera': next_seg.camera_id
                    }
                ))
        
        return events
    
    def get_timeline(self, global_id: str) -> Optional[PersonTimeline]:
        """Get timeline for a specific person."""
        return self.timelines.get(global_id)
    
    def search_by_time(self, start_time: datetime,
                       end_time: datetime) -> List[PersonTimeline]:
        """Find all persons active during a time range."""
        results = []
        for timeline in self.timelines.values():
            segments = timeline.get_segments_in_time_range(start_time, end_time)
            if segments:
                results.append(timeline)
        return results
    
    def search_by_camera(self, camera_id: int) -> List[PersonTimeline]:
        """Find all persons who visited a camera."""
        results = []
        for timeline in self.timelines.values():
            if camera_id in timeline.cameras_visited:
                results.append(timeline)
        return results
    
    def get_statistics(self) -> Dict:
        """Get timeline statistics."""
        if not self.timelines:
            return {'total_persons': 0}
        
        total_segments = sum(len(tl.segments) for tl in self.timelines.values())
        avg_segments = total_segments / len(self.timelines) if self.timelines else 0
        
        # Dwell time statistics
        dwell_times = []
        for tl in self.timelines.values():
            for seg in tl.segments:
                dwell_times.append(seg.duration)
        
        return {
            'total_persons': len(self.timelines),
            'total_segments': total_segments,
            'avg_segments_per_person': avg_segments,
            'avg_dwell_time': np.mean(dwell_times) if dwell_times else 0,
            'max_dwell_time': max(dwell_times) if dwell_times else 0,
            'total_cameras_visited': len(set(
                cam for tl in self.timelines.values() 
                for cam in tl.cameras_visited
            ))
        }