# search/aggregators.py
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import json

class ResultAggregator:
    """
    Aggregate search results for summaries.
    """
    
    def aggregate(self, results: List[Dict], query: Any) -> Dict:
        """
        Aggregate results into summary statistics.
        """
        if not results:
            return {
                'total': 0,
                'summary': {}
            }
        
        # Determine result type
        result_type = 'unknown'
        if results and 'global_id' in results[0]:
            if 'event_type' in results[0]:
                result_type = 'events'
            elif 'from_camera' in results[0]:
                result_type = 'transitions'
            else:
                result_type = 'persons'
        
        # Aggregate based on type
        if result_type == 'persons':
            return self._aggregate_persons(results)
        elif result_type == 'events':
            return self._aggregate_events(results)
        elif result_type == 'transitions':
            return self._aggregate_transitions(results)
        else:
            return self._aggregate_generic(results)
    
    def _aggregate_persons(self, results: List[Dict]) -> Dict:
        """Aggregate person results."""
        total_duration = sum(r.get('total_duration', 0) for r in results)
        
        # Camera visits
        camera_visits = defaultdict(int)
        for r in results:
            cameras = r.get('cameras_visited', [])
            if isinstance(cameras, str):
                cameras = json.loads(cameras)
            for cam in cameras:
                camera_visits[cam] += 1
        
        # Time distribution
        time_distribution = defaultdict(int)
        for r in results:
            first_seen = r.get('first_seen')
            if first_seen:
                if isinstance(first_seen, str):
                    first_seen = datetime.fromisoformat(first_seen)
                hour = first_seen.hour
                time_distribution[hour] += 1
        
        # Confidence distribution
        confidences = [r.get('confidence', 0) for r in results]
        
        return {
            'total': len(results),
            'total_duration': total_duration,
            'avg_duration': total_duration / len(results) if results else 0,
            'camera_visits': dict(camera_visits),
            'time_distribution': dict(time_distribution),
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0
        }
    
    def _aggregate_events(self, results: List[Dict]) -> Dict:
        """Aggregate event results."""
        # Event type distribution
        event_types = defaultdict(int)
        for r in results:
            event_type = r.get('event_type', 'unknown')
            event_types[event_type] += 1
        
        # Camera distribution
        camera_distribution = defaultdict(int)
        for r in results:
            camera_id = r.get('camera_id', -1)
            camera_distribution[camera_id] += 1
        
        # Time distribution
        time_distribution = defaultdict(int)
        for r in results:
            timestamp = r.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                hour = timestamp.hour
                time_distribution[hour] += 1
        
        # Person distribution
        person_distribution = defaultdict(int)
        for r in results:
            global_id = r.get('global_id', 'unknown')
            person_distribution[global_id] += 1
        
        return {
            'total': len(results),
            'event_types': dict(event_types),
            'camera_distribution': dict(camera_distribution),
            'time_distribution': dict(time_distribution),
            'person_distribution': dict(person_distribution),
            'unique_persons': len(person_distribution),
            'unique_cameras': len(camera_distribution)
        }
    
    def _aggregate_transitions(self, results: List[Dict]) -> Dict:
        """Aggregate transition results."""
        # Transition count
        transition_counts = defaultdict(int)
        for r in results:
            key = (r.get('from_camera'), r.get('to_camera'))
            transition_counts[key] += 1
        
        # Duration statistics
        durations = [r.get('duration', 0) for r in results]
        
        # Confidence statistics
        confidences = [r.get('confidence', 0) for r in results]
        
        # Person distribution
        person_distribution = defaultdict(int)
        for r in results:
            global_id = r.get('global_id', 'unknown')
            person_distribution[global_id] += 1
        
        return {
            'total': len(results),
            'transition_counts': {
                f"{k[0]}->{k[1]}": v for k, v in transition_counts.items()
            },
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'unique_persons': len(person_distribution),
            'unique_transitions': len(transition_counts)
        }
    
    def _aggregate_generic(self, results: List[Dict]) -> Dict:
        """Generic aggregation for unknown result types."""
        return {
            'total': len(results),
            'summary': 'Generic results (no specific aggregation available)'
        }