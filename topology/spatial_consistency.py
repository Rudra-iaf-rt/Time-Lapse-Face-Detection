# topology/spatial_consistency.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .camera_graph import CameraGraph

class SpatialConsistencyChecker:
    """
    Check spatial consistency for cross-camera identity matching.
    """
    
    def __init__(self, camera_graph: CameraGraph,
                 max_time_gap: float = 300.0,
                 min_probability: float = 0.1):
        """
        Initialize spatial consistency checker.
        
        Args:
            camera_graph: Camera topology graph
            max_time_gap: Maximum allowed time gap (seconds)
            min_probability: Minimum transition probability to consider
        """
        self.camera_graph = camera_graph
        self.max_time_gap = max_time_gap
        self.min_probability = min_probability
        
    def check_consistency(self, camera1: int, camera2: int,
                         time1: datetime, time2: datetime) -> Dict:
        """
        Check spatial consistency between two observations.
        
        Returns:
            Dictionary with consistency score and details
        """
        # Calculate time difference
        time_diff = abs((time2 - time1).total_seconds())
        
        # Determine direction
        if time1 < time2:
            from_camera = camera1
            to_camera = camera2
        else:
            from_camera = camera2
            to_camera = camera1
        
        # Get transition
        transition = self.camera_graph.get_transition(from_camera, to_camera)
        
        if transition is None:
            return {
                'is_consistent': False,
                'score': 0.0,
                'reason': 'No known transition',
                'time_diff': time_diff
            }
        
        # Check probability threshold
        if transition.transition_probability < self.min_probability:
            return {
                'is_consistent': False,
                'score': transition.transition_probability,
                'reason': 'Low transition probability',
                'time_diff': time_diff
            }
        
        # Check time constraints
        is_within_time = self.camera_graph.is_transition_possible(
            from_camera, to_camera, time_diff
        )
        
        # Compute spatial score
        spatial_score = self.camera_graph.compute_spatial_score(
            from_camera, to_camera, time_diff
        )
        
        return {
            'is_consistent': spatial_score > 0.3,
            'score': spatial_score,
            'time_diff': time_diff,
            'transition': transition,
            'expected_time': transition.avg_travel_time,
            'time_range': (transition.min_travel_time, transition.max_travel_time),
            'is_within_time': is_within_time
        }
    
    def get_spatial_penalty(self, camera1: int, camera2: int,
                           time1: datetime, time2: datetime) -> float:
        """
        Get spatial penalty for matching two observations.
        
        Returns:
            Penalty score (0.0 = no penalty, 1.0 = maximum penalty)
        """
        result = self.check_consistency(camera1, camera2, time1, time2)
        
        if not result['is_consistent']:
            return 1.0
        
        # Convert score to penalty (lower score = higher penalty)
        penalty = 1.0 - result['score']
        return float(penalty)
    
    def get_possible_matches(self, camera_id: int, 
                            time: datetime) -> List[Tuple[int, float]]:
        """
        Get possible cameras that could match this observation.
        
        Returns:
            List of (camera_id, probability) tuples
        """
        possible = []
        
        # Get all transitions from this camera
        destinations = self.camera_graph.get_possible_destinations(camera_id)
        
        for dest in destinations:
            transition = self.camera_graph.get_transition(camera_id, dest)
            if transition and transition.transition_probability > self.min_probability:
                possible.append((dest, transition.transition_probability))
        
        # Get all transitions to this camera
        sources = self.camera_graph.get_possible_sources(camera_id)
        
        for source in sources:
            transition = self.camera_graph.get_transition(source, camera_id)
            if transition and transition.transition_probability > self.min_probability:
                possible.append((source, transition.transition_probability))
        
        # Sort by probability
        possible.sort(key=lambda x: x[1], reverse=True)
        
        return possible
    
    def compute_camera_similarity(self, camera1: int, camera2: int) -> float:
        """
        Compute similarity between two cameras based on topology.
        """
        # Check both directions
        prob1 = self.camera_graph.get_transition_probability(camera1, camera2)
        prob2 = self.camera_graph.get_transition_probability(camera2, camera1)
        
        # Average of both directions
        return float((prob1 + prob2) / 2)