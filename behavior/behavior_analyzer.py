# behavior/behavior_analyzer.py
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from dataclasses import dataclass

@dataclass
class BehaviorProfile:
    """Behavioral profile for a person."""
    global_id: str
    activity_patterns: Dict[str, float]  # hourly activity distribution
    camera_preferences: Dict[int, float]  # camera visit frequency
    transition_patterns: Dict[Tuple[int, int], float]  # transition frequency
    dwell_patterns: Dict[int, float]  # dwell time by camera
    typical_route: List[int]
    visit_frequency: float  # visits per day
    typical_duration: float  # typical visit duration
    preferred_hours: List[int]  # hours of highest activity
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'global_id': self.global_id,
            'activity_patterns': self.activity_patterns,
            'camera_preferences': self.camera_preferences,
            'transition_patterns': {
                f"{k[0]}->{k[1]}": v 
                for k, v in self.transition_patterns.items()
            },
            'dwell_patterns': self.dwell_patterns,
            'typical_route': self.typical_route,
            'visit_frequency': self.visit_frequency,
            'typical_duration': self.typical_duration,
            'preferred_hours': self.preferred_hours,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class BehaviorAnalyzer:
    """
    Analyze and build behavioral profiles for persons.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.profiles: Dict[str, BehaviorProfile] = {}
        self.min_observations = self.config.get('min_observations', 5)
        self.analysis_window = self.config.get('analysis_window', 30)  # days
        
    def build_profile(self, timeline_data: Dict) -> BehaviorProfile:
        """
        Build a behavioral profile from timeline data.
        
        Args:
            timeline_data: Person timeline data with segments and events
            
        Returns:
            BehaviorProfile object
        """
        global_id = timeline_data.get('global_id')
        segments = timeline_data.get('segments', [])
        
        if not segments:
            return BehaviorProfile(
                global_id=global_id,
                activity_patterns={},
                camera_preferences={},
                transition_patterns={},
                dwell_patterns={},
                typical_route=[],
                visit_frequency=0.0,
                typical_duration=0.0,
                preferred_hours=[]
            )
        
        # 1. Activity patterns (hourly)
        activity_patterns = self._compute_activity_patterns(segments)
        
        # 2. Camera preferences
        camera_preferences = self._compute_camera_preferences(segments)
        
        # 3. Transition patterns
        transition_patterns = self._compute_transition_patterns(segments)
        
        # 4. Dwell patterns
        dwell_patterns = self._compute_dwell_patterns(segments)
        
        # 5. Typical route
        typical_route = self._find_typical_route(segments)
        
        # 6. Visit frequency
        visit_frequency = self._compute_visit_frequency(segments)
        
        # 7. Typical duration
        typical_duration = self._compute_typical_duration(segments)
        
        # 8. Preferred hours
        preferred_hours = self._find_preferred_hours(activity_patterns)
        
        profile = BehaviorProfile(
            global_id=global_id,
            activity_patterns=activity_patterns,
            camera_preferences=camera_preferences,
            transition_patterns=transition_patterns,
            dwell_patterns=dwell_patterns,
            typical_route=typical_route,
            visit_frequency=visit_frequency,
            typical_duration=typical_duration,
            preferred_hours=preferred_hours,
            last_updated=datetime.now()
        )
        
        self.profiles[global_id] = profile
        return profile
    
    def _compute_activity_patterns(self, segments: List[Dict]) -> Dict[str, float]:
        """Compute hourly activity distribution."""
        hourly_activity = defaultdict(float)
        total_duration = 0
        
        for seg in segments:
            start = datetime.fromisoformat(seg['start_time'])
            end = datetime.fromisoformat(seg['end_time'])
            duration = seg.get('duration', 0)
            
            hour = start.hour
            hourly_activity[hour] += duration
            total_duration += duration
        
        # Normalize
        if total_duration > 0:
            for hour in hourly_activity:
                hourly_activity[hour] /= total_duration
        
        return dict(hourly_activity)
    
    def _compute_camera_preferences(self, segments: List[Dict]) -> Dict[int, float]:
        """Compute camera visit frequency."""
        camera_counts = defaultdict(int)
        total_visits = 0
        
        for seg in segments:
            camera_id = seg['camera_id']
            camera_counts[camera_id] += 1
            total_visits += 1
        
        # Normalize
        if total_visits > 0:
            for cam in camera_counts:
                camera_counts[cam] /= total_visits
        
        return dict(camera_counts)
    
    def _compute_transition_patterns(self, segments: List[Dict]) -> Dict[Tuple[int, int], float]:
        """Compute transition patterns between cameras."""
        transitions = defaultdict(int)
        total_transitions = 0
        
        for i in range(len(segments) - 1):
            current_cam = segments[i]['camera_id']
            next_cam = segments[i + 1]['camera_id']
            
            if current_cam != next_cam:
                key = (current_cam, next_cam)
                transitions[key] += 1
                total_transitions += 1
        
        # Normalize
        if total_transitions > 0:
            for key in transitions:
                transitions[key] /= total_transitions
        
        return dict(transitions)
    
    def _compute_dwell_patterns(self, segments: List[Dict]) -> Dict[int, float]:
        """Compute average dwell time by camera."""
        dwell_times = defaultdict(list)
        
        for seg in segments:
            camera_id = seg['camera_id']
            duration = seg.get('duration', 0)
            if duration > 0:
                dwell_times[camera_id].append(duration)
        
        # Compute averages
        avg_dwell = {}
        for cam, durations in dwell_times.items():
            avg_dwell[cam] = np.mean(durations)
        
        return avg_dwell
    
    def _find_typical_route(self, segments: List[Dict]) -> List[int]:
        """Find the most common route."""
        routes = []
        current_route = []
        
        for seg in segments:
            camera_id = seg['camera_id']
            if not current_route or current_route[-1] != camera_id:
                current_route.append(camera_id)
            else:
                # Same camera - could be dwell, keep going
                pass
        
        # Return the complete route
        return current_route
    
    def _compute_visit_frequency(self, segments: List[Dict]) -> float:
        """Compute visits per day."""
        if not segments:
            return 0.0
        
        # Get unique visit days
        visit_days = set()
        for seg in segments:
            start = datetime.fromisoformat(seg['start_time'])
            day_key = start.strftime('%Y-%m-%d')
            visit_days.add(day_key)
        
        # Calculate total days in range
        if len(segments) >= 2:
            first = datetime.fromisoformat(segments[0]['start_time'])
            last = datetime.fromisoformat(segments[-1]['start_time'])
            total_days = (last - first).days + 1
        else:
            total_days = 1
        
        return len(visit_days) / total_days if total_days > 0 else 0
    
    def _compute_typical_duration(self, segments: List[Dict]) -> float:
        """Compute typical visit duration."""
        if not segments:
            return 0.0
        
        durations = [seg.get('duration', 0) for seg in segments if seg.get('duration', 0) > 0]
        if durations:
            return np.median(durations)
        return 0.0
    
    def _find_preferred_hours(self, activity_patterns: Dict[str, float]) -> List[int]:
        """Find preferred hours based on activity distribution."""
        if not activity_patterns:
            return []
        
        # Sort hours by activity
        sorted_hours = sorted(activity_patterns.items(), 
                            key=lambda x: x[1], reverse=True)
        
        # Take top 3 hours
        return [int(hour) for hour, _ in sorted_hours[:3]]
    
    def get_profile(self, global_id: str) -> Optional[BehaviorProfile]:
        """Get behavioral profile for a person."""
        return self.profiles.get(global_id)
    
    def get_all_profiles(self) -> Dict[str, BehaviorProfile]:
        """Get all behavioral profiles."""
        return self.profiles
    
    def compare_profiles(self, profile1: BehaviorProfile, 
                        profile2: BehaviorProfile) -> float:
        """
        Compare two behavioral profiles.
        
        Returns:
            Similarity score (0-1)
        """
        if not profile1 or not profile2:
            return 0.0
        
        # Compare camera preferences
        cam_sim = self._compare_distributions(
            profile1.camera_preferences,
            profile2.camera_preferences
        )
        
        # Compare activity patterns
        activity_sim = self._compare_distributions(
            profile1.activity_patterns,
            profile2.activity_patterns
        )
        
        # Compare dwell patterns
        dwell_sim = self._compare_distributions(
            profile1.dwell_patterns,
            profile2.dwell_patterns
        )
        
        # Compare routes
        route_sim = self._compare_routes(
            profile1.typical_route,
            profile2.typical_route
        )
        
        # Weighted average
        weights = [0.3, 0.2, 0.2, 0.3]
        similarity = (cam_sim * weights[0] + 
                     activity_sim * weights[1] + 
                     dwell_sim * weights[2] + 
                     route_sim * weights[3])
        
        return similarity
    
    def _compare_distributions(self, dist1: Dict, dist2: Dict) -> float:
        """Compare two probability distributions."""
        if not dist1 or not dist2:
            return 0.0
        
        # Get union of keys
        keys = set(dist1.keys()) | set(dist2.keys())
        if not keys:
            return 0.0
        
        # Compute similarity
        similarity = 0.0
        for key in keys:
            val1 = dist1.get(key, 0)
            val2 = dist2.get(key, 0)
            similarity += min(val1, val2)
        
        return similarity / len(keys)
    
    def _compare_routes(self, route1: List[int], route2: List[int]) -> float:
        """Compare two routes."""
        if not route1 or not route2:
            return 0.0
        
        # Find longest common subsequence
        m, n = len(route1), len(route2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if route1[i-1] == route2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        max_length = max(m, n)
        
        return lcs_length / max_length if max_length > 0 else 0.0