# timeline/timeline_aggregator.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from .timeline_builder import PersonTimeline, TimelineSegment, TimelineEvent

class TimelineAggregator:
    """
    Aggregate and summarize person timelines.
    """
    
    def __init__(self, time_bucket: int = 60):  # 1 minute buckets
        self.time_bucket = time_bucket
    
    def aggregate_by_time(self, timeline: PersonTimeline,
                          bucket_size: int = 60) -> Dict:
        """
        Aggregate timeline into time buckets.
        
        Args:
            timeline: Person timeline
            bucket_size: Bucket size in seconds
            
        Returns:
            Dictionary with time buckets and activity
        """
        if not timeline.segments:
            return {}
        
        # Determine time range
        start = timeline.first_seen
        end = timeline.last_seen
        
        if not start or not end:
            return {}
        
        # Create buckets
        buckets = {}
        current = start
        while current <= end:
            bucket_key = current.strftime('%Y-%m-%d %H:%M:%S')
            buckets[bucket_key] = {
                'timestamp': current,
                'camera_id': None,
                'duration': 0,
                'events': []
            }
            current += timedelta(seconds=bucket_size)
        
        # Fill buckets with segment data
        for segment in timeline.segments:
            seg_start = segment.start_time
            seg_end = segment.end_time
            
            # Find buckets that overlap with this segment
            current_time = seg_start
            while current_time <= seg_end:
                bucket_key = current_time.strftime('%Y-%m-%d %H:%M:%S')
                if bucket_key in buckets:
                    # Calculate overlap duration
                    bucket_end = current_time + timedelta(seconds=bucket_size)
                    overlap_end = min(seg_end, bucket_end)
                    overlap_duration = (overlap_end - current_time).total_seconds()
                    
                    buckets[bucket_key]['camera_id'] = segment.camera_id
                    buckets[bucket_key]['duration'] += overlap_duration
                    buckets[bucket_key]['events'].extend(segment.events)
                
                current_time += timedelta(seconds=bucket_size)
        
        return buckets
    
    def aggregate_by_camera(self, timeline: PersonTimeline) -> Dict:
        """
        Aggregate timeline by camera.
        
        Returns:
            Dictionary with camera-wise statistics
        """
        if not timeline.segments:
            return {}
        
        camera_stats = defaultdict(lambda: {
            'total_duration': 0,
            'visit_count': 0,
            'first_visit': None,
            'last_visit': None,
            'segments': []
        })
        
        for segment in timeline.segments:
            cam_id = segment.camera_id
            stats = camera_stats[cam_id]
            
            stats['total_duration'] += segment.duration
            stats['visit_count'] += 1
            stats['segments'].append(segment)
            
            if stats['first_visit'] is None or segment.start_time < stats['first_visit']:
                stats['first_visit'] = segment.start_time
            if stats['last_visit'] is None or segment.end_time > stats['last_visit']:
                stats['last_visit'] = segment.end_time
        
        return dict(camera_stats)
    
    def get_activity_patterns(self, timeline: PersonTimeline) -> Dict:
        """
        Get activity patterns from timeline.
        
        Returns:
            Dictionary with pattern information
        """
        if not timeline.segments:
            return {}
        
        # Hourly activity
        hourly_activity = defaultdict(float)
        for segment in timeline.segments:
            hour = segment.start_time.hour
            hourly_activity[hour] += segment.duration
        
        # Daily activity (day of week)
        daily_activity = defaultdict(float)
        for segment in timeline.segments:
            day = segment.start_time.weekday()
            daily_activity[day] += segment.duration
        
        # Camera transition patterns
        transitions = defaultdict(int)
        for i in range(len(timeline.segments) - 1):
            current = timeline.segments[i]
            next_seg = timeline.segments[i + 1]
            if current.camera_id != next_seg.camera_id:
                key = (current.camera_id, next_seg.camera_id)
                transitions[key] += 1
        
        return {
            'hourly_activity': dict(hourly_activity),
            'daily_activity': dict(daily_activity),
            'transition_patterns': dict(transitions),
            'most_active_hour': max(hourly_activity.items(), 
                                   key=lambda x: x[1])[0] if hourly_activity else None,
            'most_active_day': max(daily_activity.items(),
                                  key=lambda x: x[1])[0] if daily_activity else None
        }
    
    def get_visit_summary(self, timeline: PersonTimeline) -> Dict:
        """
        Get a concise visit summary.
        
        Returns:
            Dictionary with summarized visits
        """
        if not timeline.segments:
            return {
                'global_id': timeline.global_id,
                'total_visits': 0,
                'visits': []
            }
        
        visits = []
        for segment in timeline.segments:
            visits.append({
                'camera': segment.camera_id,
                'start': segment.start_time.isoformat(),
                'end': segment.end_time.isoformat(),
                'duration': segment.duration,
                'confidence': segment.confidence
            })
        
        return {
            'global_id': timeline.global_id,
            'total_visits': len(visits),
            'total_duration': timeline.total_duration,
            'unique_cameras': len(timeline.cameras_visited),
            'first_seen': timeline.first_seen.isoformat() if timeline.first_seen else None,
            'last_seen': timeline.last_seen.isoformat() if timeline.last_seen else None,
            'route': timeline.route,
            'visits': visits
        }