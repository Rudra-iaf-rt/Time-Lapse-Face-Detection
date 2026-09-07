# timeline/route_analyzer.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from .timeline_builder import PersonTimeline

@dataclass
class Route:
    """A movement route."""
    cameras: List[int]
    start_time: datetime
    end_time: datetime
    duration: float
    person_id: str
    
    def to_dict(self) -> Dict:
        return {
            'cameras': self.cameras,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': self.duration,
            'person_id': self.person_id
        }

class RouteAnalyzer:
    """
    Analyze movement routes and patterns.
    """
    
    def __init__(self):
        self.routes: List[Route] = []
    
    def extract_routes(self, timeline: PersonTimeline) -> List[Route]:
        """
        Extract movement routes from a timeline.
        """
        routes = []
        
        if len(timeline.segments) < 2:
            return routes
        
        # Extract consecutive camera visits as routes
        current_route = [timeline.segments[0].camera_id]
        current_start = timeline.segments[0].start_time
        
        for i in range(1, len(timeline.segments)):
            prev_seg = timeline.segments[i-1]
            curr_seg = timeline.segments[i]
            
            # Check if cameras are different
            if prev_seg.camera_id != curr_seg.camera_id:
                # End current route
                route = Route(
                    cameras=current_route,
                    start_time=current_start,
                    end_time=prev_seg.end_time,
                    duration=(prev_seg.end_time - current_start).total_seconds(),
                    person_id=timeline.global_id
                )
                routes.append(route)
                
                # Start new route
                current_route = [curr_seg.camera_id]
                current_start = curr_seg.start_time
            else:
                # Same camera - add to route if not already in route
                if curr_seg.camera_id not in current_route:
                    current_route.append(curr_seg.camera_id)
        
        # Add final route if it has at least 2 cameras
        if len(current_route) >= 2:
            route = Route(
                cameras=current_route,
                start_time=current_start,
                end_time=timeline.segments[-1].end_time,
                duration=(timeline.segments[-1].end_time - current_start).total_seconds(),
                person_id=timeline.global_id
            )
            routes.append(route)
        
        self.routes.extend(routes)
        return routes
    
    def find_common_routes(self, timelines: List[PersonTimeline],
                           min_occurrences: int = 2) -> List[Dict]:
        """
        Find common routes across multiple persons.
        """
        route_counter = defaultdict(lambda: {'count': 0, 'examples': []})
        
        for timeline in timelines:
            routes = self.extract_routes(timeline)
            for route in routes:
                route_key = tuple(route.cameras)
                route_counter[route_key]['count'] += 1
                if len(route_counter[route_key]['examples']) < 5:
                    route_counter[route_key]['examples'].append(route.to_dict())
        
        # Filter by minimum occurrences
        common_routes = []
        for route_key, data in route_counter.items():
            if data['count'] >= min_occurrences:
                common_routes.append({
                    'route': list(route_key),
                    'occurrences': data['count'],
                    'examples': data['examples']
                })
        
        # Sort by occurrences
        common_routes.sort(key=lambda x: x['occurrences'], reverse=True)
        return common_routes
    
    def analyze_route_patterns(self, routes: List[Route]) -> Dict:
        """
        Analyze route patterns.
        """
        if not routes:
            return {'total_routes': 0}
        
        route_lengths = [len(r.cameras) for r in routes]
        route_durations = [r.duration for r in routes]
        
        # Find most common paths
        path_counter = defaultdict(int)
        for route in routes:
            path_counter[tuple(route.cameras)] += 1
        
        most_common = max(path_counter.items(), key=lambda x: x[1]) if path_counter else None
        
        return {
            'total_routes': len(routes),
            'avg_route_length': np.mean(route_lengths),
            'max_route_length': max(route_lengths) if route_lengths else 0,
            'avg_route_duration': np.mean(route_durations),
            'most_common_route': list(most_common[0]) if most_common else None,
            'most_common_route_count': most_common[1] if most_common else 0,
            'unique_routes': len(path_counter)
        }
    
    def predict_next_camera(self, current_camera: int, 
                           recent_cameras: List[int],
                           topology: Dict) -> List[Tuple[int, float]]:
        """
        Predict the next camera based on historical patterns.
        
        Args:
            current_camera: Current camera ID
            recent_cameras: List of recent cameras in sequence
            topology: Camera topology probabilities
            
        Returns:
            List of (camera_id, probability) tuples
        """
        predictions = defaultdict(float)
        
        # 1. Use topology probabilities
        if current_camera in topology:
            for next_cam, prob in topology[current_camera].items():
                predictions[next_cam] += prob * 0.6
        
        # 2. Use historical route patterns
        if len(recent_cameras) >= 2:
            # Look for similar sequences
            pattern = tuple(recent_cameras[-2:])
            
            # Find routes that start with this pattern
            for route in self.routes:
                route_cameras = tuple(route.cameras)
                if len(route_cameras) >= len(pattern) + 1:
                    if route_cameras[:len(pattern)] == pattern:
                        next_cam = route_cameras[len(pattern)]
                        predictions[next_cam] += 0.3
        
        # 3. Use frequency of transitions
        if len(recent_cameras) >= 3:
            last_three = tuple(recent_cameras[-3:])
            for route in self.routes:
                route_cameras = tuple(route.cameras)
                if len(route_cameras) >= 4:
                    if route_cameras[:3] == last_three:
                        next_cam = route_cameras[3]
                        predictions[next_cam] += 0.1
        
        # Normalize probabilities
        total = sum(predictions.values())
        if total > 0:
            predictions = {cam: prob/total for cam, prob in predictions.items()}
        
        # Sort by probability
        sorted_predictions = sorted(predictions.items(), 
                                   key=lambda x: x[1], reverse=True)
        
        return sorted_predictions[:5]  # Top 5 predictions