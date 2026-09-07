# topology/transition_learner.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import sqlite3

from .camera_graph import CameraGraph, CameraTransition

class TransitionLearner:
    """
    Learn camera transitions from tracking data.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self.track_history = defaultdict(list)
        self.temporal_window = 300  # 5 minutes default
    
    def learn_from_tracks(self, min_observations: int = 3,
                          max_time_gap: float = 300.0) -> CameraGraph:
        """
        Learn camera transitions from track history.
        
        Args:
            min_observations: Minimum observations to consider a transition
            max_time_gap: Maximum time gap between observations (seconds)
        
        Returns:
            CameraGraph with learned transitions
        """
        graph = CameraGraph(self.db_path)
        
        # Group tracks by global identity
        identity_tracks = self._group_by_identity()
        
        # Analyze each identity's trajectory
        transitions = defaultdict(list)
        
        for identity, tracks in identity_tracks.items():
            # Sort tracks by time
            sorted_tracks = sorted(tracks, key=lambda x: x['timestamp'])
            
            # Find transitions between cameras
            for i in range(len(sorted_tracks) - 1):
                current = sorted_tracks[i]
                next_track = sorted_tracks[i + 1]
                
                # Check if same camera
                if current['camera_id'] == next_track['camera_id']:
                    continue
                
                # Check time gap
                time_diff = (next_track['timestamp'] - current['timestamp']).total_seconds()
                if time_diff > max_time_gap:
                    continue
                
                # Record transition
                key = (current['camera_id'], next_track['camera_id'])
                transitions[key].append({
                    'time_diff': time_diff,
                    'identity': identity,
                    'timestamp': next_track['timestamp']
                })
        
        # Build transitions
        for (from_cam, to_cam), observations in transitions.items():
            if len(observations) < min_observations:
                continue
            
            # Calculate statistics
            time_diffs = [obs['time_diff'] for obs in observations]
            
            transition = CameraTransition(
                from_camera=from_cam,
                to_camera=to_cam,
                transition_probability=len(observations) / len(identity_tracks),
                avg_travel_time=np.mean(time_diffs),
                min_travel_time=min(time_diffs),
                max_travel_time=max(time_diffs),
                std_travel_time=np.std(time_diffs),
                observation_count=len(observations),
                last_observed=max(obs['timestamp'] for obs in observations)
            )
            
            graph.add_transition(from_cam, to_cam, transition)
        
        # Normalize probabilities
        self._normalize_probabilities(graph)
        
        return graph
    
    def _group_by_identity(self) -> Dict:
        """Group tracks by global identity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Query tracks with global IDs
        cursor.execute('''
            SELECT 
                rp.global_id,
                rp.camera_id,
                rp.track_id,
                rp.timestamp,
                rp.embedding
            FROM reid_profiles rp
            WHERE rp.global_id IS NOT NULL
            ORDER BY rp.timestamp
        ''')
        
        identity_tracks = defaultdict(list)
        
        for row in cursor.fetchall():
            global_id, camera_id, track_id, timestamp, embedding = row
            
            identity_tracks[global_id].append({
                'camera_id': camera_id,
                'track_id': track_id,
                'timestamp': datetime.fromisoformat(timestamp),
                'embedding': embedding
            })
        
        conn.close()
        return identity_tracks
    
    def _normalize_probabilities(self, graph: CameraGraph):
        """Normalize transition probabilities for each camera."""
        # Get all cameras
        cameras = set()
        for (from_cam, to_cam) in graph.transitions.keys():
            cameras.add(from_cam)
            cameras.add(to_cam)
        
        # Normalize outgoing transitions
        for camera in cameras:
            outgoing = []
            for (from_cam, to_cam), transition in graph.transitions.items():
                if from_cam == camera:
                    outgoing.append((to_cam, transition))
            
            if outgoing:
                total_prob = sum(t.transition_probability for _, t in outgoing)
                if total_prob > 0:
                    for to_cam, transition in outgoing:
                        transition.transition_probability /= total_prob
    
    def add_observation(self, global_id: str, camera_id: int,
                       timestamp: datetime):
        """Add an observation for learning."""
        self.track_history[global_id].append({
            'camera_id': camera_id,
            'timestamp': timestamp
        })
    
    def get_transition_statistics(self, from_camera: int, 
                                  to_camera: int) -> Dict:
        """Get statistics for a specific transition."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as count,
                AVG(travel_time) as avg_time,
                MIN(travel_time) as min_time,
                MAX(travel_time) as max_time,
                STDDEV(travel_time) as std_time
            FROM (
                SELECT 
                    (t2.timestamp - t1.timestamp) as travel_time
                FROM reid_profiles t1
                JOIN reid_profiles t2 
                    ON t1.global_id = t2.global_id
                WHERE t1.camera_id = ? 
                    AND t2.camera_id = ?
                    AND t1.timestamp < t2.timestamp
                    AND t2.timestamp - t1.timestamp < 300  -- 5 minutes
                ORDER BY t1.timestamp
            )
        ''', (from_camera, to_camera))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] > 0:
            return {
                'count': result[0],
                'avg_time': result[1],
                'min_time': result[2],
                'max_time': result[3],
                'std_time': result[4]
            }
        
        return None