# timeline/event_detector.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .timeline_builder import PersonTimeline, TimelineEvent, TimelineSegment

class EventDetector:
    """
    Detect significant events in person timelines.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Thresholds
        self.dwell_threshold = self.config.get('dwell_threshold', 300)  # 5 minutes
        self.transition_threshold = self.config.get('transition_threshold', 10)  # 10 seconds
        
    def detect_events(self, timeline: PersonTimeline) -> Dict:
        """
        Detect all types of events in a timeline.
        
        Returns:
            Dictionary with categorized events
        """
        return {
            'dwell_events': self.detect_dwell_events(timeline),
            'transition_events': self.detect_transition_events(timeline),
            'visit_events': self.detect_visit_events(timeline),
            'anomaly_events': self.detect_anomaly_events(timeline)
        }
    
    def detect_dwell_events(self, timeline: PersonTimeline) -> List[Dict]:
        """
        Detect long dwell events (> threshold).
        """
        dwell_events = []
        
        for segment in timeline.segments:
            if segment.duration > self.dwell_threshold:
                dwell_events.append({
                    'type': 'long_dwell',
                    'camera_id': segment.camera_id,
                    'start_time': segment.start_time.isoformat(),
                    'end_time': segment.end_time.isoformat(),
                    'duration': segment.duration,
                    'confidence': segment.confidence
                })
        
        return dwell_events
    
    def detect_transition_events(self, timeline: PersonTimeline) -> List[Dict]:
        """
        Detect transitions between cameras.
        """
        transition_events = []
        
        for i in range(len(timeline.segments) - 1):
            current = timeline.segments[i]
            next_seg = timeline.segments[i + 1]
            
            if current.camera_id != next_seg.camera_id:
                time_diff = (next_seg.start_time - current.end_time).total_seconds()
                
                # Detect fast transitions (unusual)
                event_type = 'transition'
                if time_diff < self.transition_threshold:
                    event_type = 'fast_transition'
                
                transition_events.append({
                    'type': event_type,
                    'from_camera': current.camera_id,
                    'to_camera': next_seg.camera_id,
                    'time': current.end_time.isoformat(),
                    'duration': time_diff,
                    'confidence': min(current.confidence, next_seg.confidence)
                })
        
        return transition_events
    
    def detect_visit_events(self, timeline: PersonTimeline) -> List[Dict]:
        """
        Detect visit patterns.
        """
        visit_events = []
        
        # Count visits per camera
        visit_counts = defaultdict(int)
        for segment in timeline.segments:
            visit_counts[segment.camera_id] += 1
        
        # Detect return visits
        for segment in timeline.segments:
            if visit_counts.get(segment.camera_id, 0) > 1:
                visit_events.append({
                    'type': 'return_visit',
                    'camera_id': segment.camera_id,
                    'visit_count': visit_counts[segment.camera_id],
                    'last_visit': segment.end_time.isoformat()
                })
        
        return visit_events
    
    def detect_anomaly_events(self, timeline: PersonTimeline) -> List[Dict]:
        """
        Detect anomalous events.
        """
        anomaly_events = []
        
        # 1. Very long dwell
        dwell_events = self.detect_dwell_events(timeline)
        for event in dwell_events:
            if event['duration'] > self.dwell_threshold * 3:  # 15+ minutes
                anomaly_events.append({
                    'type': 'abnormal_dwell',
                    **event,
                    'severity': 'high'
                })
        
        # 2. Unusual time (after hours)
        for segment in timeline.segments:
            hour = segment.start_time.hour
            if hour < 6 or hour > 22:  # Between 10 PM and 6 AM
                anomaly_events.append({
                    'type': 'after_hours_presence',
                    'camera_id': segment.camera_id,
                    'time': segment.start_time.isoformat(),
                    'duration': segment.duration,
                    'severity': 'medium'
                })
        
        # 3. Rapid camera switching
        transitions = self.detect_transition_events(timeline)
        for event in transitions:
            if event['duration'] < 5:  # Less than 5 seconds
                anomaly_events.append({
                    'type': 'rapid_transition',
                    **event,
                    'severity': 'medium'
                })
        
        return anomaly_events
    
    def detect_patterns(self, timelines: Dict[str, PersonTimeline]) -> Dict:
        """
        Detect patterns across multiple timelines.
        """
        patterns = {
            'common_routes': self._find_common_routes(timelines),
            'crowd_movements': self._find_crowd_movements(timelines),
            'cooccurrence': self._find_cooccurrence(timelines)
        }
        
        return patterns
    
    def _find_common_routes(self, timelines: Dict[str, PersonTimeline]) -> List[Dict]:
        """Find common routes across persons."""
        route_counts = defaultdict(int)
        
        for timeline in timelines.values():
            route = tuple(timeline.route)
            if len(route) >= 2:
                route_counts[route] += 1
        
        # Sort by frequency
        common_routes = []
        for route, count in sorted(route_counts.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]:
            common_routes.append({
                'route': list(route),
                'count': count,
                'length': len(route)
            })
        
        return common_routes
    
    def _find_crowd_movements(self, timelines: Dict[str, PersonTimeline]) -> List[Dict]:
        """Find crowd movement patterns."""
        # Group by time buckets
        time_buckets = defaultdict(list)
        
        for timeline in timelines.values():
            for segment in timeline.segments:
                hour = segment.start_time.hour
                minute = segment.start_time.minute // 5 * 5  # 5-minute buckets
                key = f"{hour:02d}:{minute:02d}"
                time_buckets[key].append({
                    'global_id': timeline.global_id,
                    'camera_id': segment.camera_id
                })
        
        # Find high activity periods
        crowd_movements = []
        for time_key, activities in time_buckets.items():
            if len(activities) > 5:  # More than 5 people
                # Group by camera
                camera_counts = defaultdict(int)
                for activity in activities:
                    camera_counts[activity['camera_id']] += 1
                
                crowd_movements.append({
                    'time': time_key,
                    'total_people': len(activities),
                    'camera_distribution': dict(camera_counts)
                })
        
        return crowd_movements
    
    def _find_cooccurrence(self, timelines: Dict[str, PersonTimeline]) -> List[Dict]:
        """Find persons who are often seen together."""
        cooccurrence = defaultdict(lambda: defaultdict(int))
        
        # For each camera, find overlapping visits
        for timeline in timelines.values():
            for segment in timeline.segments:
                # Find other persons in same camera at same time
                for other_id, other_timeline in timelines.items():
                    if other_id == timeline.global_id:
                        continue
                    
                    for other_segment in other_timeline.segments:
                        if other_segment.camera_id != segment.camera_id:
                            continue
                        
                        # Check overlap
                        if (segment.start_time <= other_segment.end_time and
                            other_segment.start_time <= segment.end_time):
                            cooccurrence[timeline.global_id][other_id] += 1
        
        # Find pairs with high cooccurrence
        pairs = []
        for person, others in cooccurrence.items():
            for other, count in others.items():
                if count >= 3:  # At least 3 cooccurrences
                    pairs.append({
                        'person1': person,
                        'person2': other,
                        'count': count
                    })
        
        return pairs