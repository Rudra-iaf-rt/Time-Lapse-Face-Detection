# behavior/pattern_learner.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

class PatternLearner:
    """
    Learn behavioral patterns from historical data.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.patterns = {
            'common_routes': [],
            'peak_hours': {},
            'camera_usage': {},
            'crowd_patterns': [],
            'temporal_patterns': {}
        }
        self.eps = self.config.get('cluster_eps', 0.3)
        self.min_samples = self.config.get('min_samples', 3)
        
    def learn_patterns(self, historical_data: List[Dict]) -> Dict:
        """
        Learn behavioral patterns from historical data.
        """
        if not historical_data:
            return self.patterns
        
        # 1. Common routes
        self.patterns['common_routes'] = self._learn_common_routes(historical_data)
        
        # 2. Peak hours
        self.patterns['peak_hours'] = self._learn_peak_hours(historical_data)
        
        # 3. Camera usage patterns
        self.patterns['camera_usage'] = self._learn_camera_usage(historical_data)
        
        # 4. Crowd patterns
        self.patterns['crowd_patterns'] = self._learn_crowd_patterns(historical_data)
        
        # 5. Temporal patterns
        self.patterns['temporal_patterns'] = self._learn_temporal_patterns(historical_data)
        
        return self.patterns
    
    def _learn_common_routes(self, data: List[Dict]) -> List[Dict]:
        """Learn common movement routes."""
        routes = []
        
        for entry in data:
            route = entry.get('route', [])
            if len(route) >= 2:
                routes.append(tuple(route))
        
        # Count route frequencies
        route_counts = defaultdict(int)
        for route in routes:
            route_counts[route] += 1
        
        # Get common routes (appear in at least 5% of data)
        threshold = len(data) * 0.05
        common_routes = []
        
        for route, count in sorted(route_counts.items(), 
                                  key=lambda x: x[1], reverse=True):
            if count >= threshold:
                common_routes.append({
                    'route': list(route),
                    'frequency': count / len(data) if data else 0,
                    'count': count
                })
        
        return common_routes[:10]  # Top 10 common routes
    
    def _learn_peak_hours(self, data: List[Dict]) -> Dict[str, List[int]]:
        """Learn peak activity hours."""
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        
        for entry in data:
            timestamp = entry.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                hour = timestamp.hour
                day = timestamp.weekday()
                hourly_activity[hour] += 1
                daily_activity[day] += 1
        
        # Find peak hours (top 3)
        peak_hours = sorted(hourly_activity.items(), 
                          key=lambda x: x[1], reverse=True)[:3]
        
        # Find peak days (top 2)
        peak_days = sorted(daily_activity.items(), 
                          key=lambda x: x[1], reverse=True)[:2]
        
        return {
            'peak_hours': [hour for hour, _ in peak_hours],
            'peak_days': [day for day, _ in peak_days],
            'hourly_distribution': dict(hourly_activity),
            'daily_distribution': dict(daily_activity)
        }
    
    def _learn_camera_usage(self, data: List[Dict]) -> Dict:
        """Learn camera usage patterns."""
        camera_counts = defaultdict(int)
        camera_dwell = defaultdict(list)
        
        for entry in data:
            camera_id = entry.get('camera_id')
            dwell_time = entry.get('dwell_time', 0)
            
            if camera_id is not None:
                camera_counts[camera_id] += 1
                if dwell_time > 0:
                    camera_dwell[camera_id].append(dwell_time)
        
        # Compute statistics
        camera_stats = {}
        for cam_id in camera_counts:
            camera_stats[cam_id] = {
                'visit_count': camera_counts[cam_id],
                'visit_frequency': camera_counts[cam_id] / len(data) if data else 0,
                'avg_dwell': np.mean(camera_dwell[cam_id]) if camera_dwell[cam_id] else 0,
                'max_dwell': np.max(camera_dwell[cam_id]) if camera_dwell[cam_id] else 0
            }
        
        return camera_stats
    
    def _learn_crowd_patterns(self, data: List[Dict]) -> List[Dict]:
        """Learn crowd movement patterns."""
        crowd_patterns = []
        
        # Group by time segments
        time_segments = defaultdict(list)
        for entry in data:
            timestamp = entry.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                # 15-minute segments
                minute = timestamp.minute // 15 * 15
                time_key = f"{timestamp.hour:02d}:{minute:02d}"
                time_segments[time_key].append(entry)
        
        # Analyze each time segment
        for time_key, entries in time_segments.items():
            if len(entries) >= self.min_samples:
                # Count cameras
                camera_counts = defaultdict(int)
                for entry in entries:
                    camera_id = entry.get('camera_id')
                    if camera_id is not None:
                        camera_counts[camera_id] += 1
                
                if len(camera_counts) >= 2:
                    crowd_patterns.append({
                        'time': time_key,
                        'total_people': len(entries),
                        'camera_distribution': dict(camera_counts),
                        'patterns': self._find_behavioral_patterns(entries)
                    })
        
        return crowd_patterns
    
    def _learn_temporal_patterns(self, data: List[Dict]) -> Dict:
        """Learn temporal patterns."""
        patterns = {}
        
        # Daily patterns
        daily_patterns = defaultdict(lambda: defaultdict(int))
        for entry in data:
            timestamp = entry.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                day = timestamp.strftime('%A')
                hour = timestamp.hour
                daily_patterns[day][hour] += 1
        
        # Weekly patterns
        weekly_patterns = defaultdict(int)
        for entry in data:
            timestamp = entry.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                week = timestamp.isocalendar()[1]
                weekly_patterns[week] += 1
        
        return {
            'daily_patterns': {day: dict(hours) for day, hours in daily_patterns.items()},
            'weekly_patterns': dict(weekly_patterns),
            'most_active_day': max(weekly_patterns.items(), 
                                  key=lambda x: x[1])[0] if weekly_patterns else None
        }
    
    def _find_behavioral_patterns(self, entries: List[Dict]) -> List[Dict]:
        """Find behavioral patterns in a group of entries."""
        patterns = []
        
        # Check for common routes
        routes = [entry.get('route', []) for entry in entries if entry.get('route')]
        if routes:
            route_freq = defaultdict(int)
            for route in routes:
                route_freq[tuple(route)] += 1
            
            most_common = max(route_freq.items(), key=lambda x: x[1])
            if most_common[1] >= len(routes) * 0.3:  # 30% follow same route
                patterns.append({
                    'type': 'common_route',
                    'route': list(most_common[0]),
                    'frequency': most_common[1] / len(routes)
                })
        
        # Check for common dwell times
        dwells = [entry.get('dwell_time', 0) for entry in entries if entry.get('dwell_time', 0) > 0]
        if dwells:
            avg_dwell = np.mean(dwells)
            std_dwell = np.std(dwells)
            
            if std_dwell < avg_dwell * 0.5:  # Low variance
                patterns.append({
                    'type': 'dwell_pattern',
                    'avg_dwell': avg_dwell,
                    'std_dwell': std_dwell
                })
        
        return patterns