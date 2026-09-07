# topology/temporal_consistency.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

class TemporalConsistencyChecker:
    """
    Check temporal consistency for identity tracking.
    """
    
    def __init__(self, max_time_gap: float = 300.0,
                 min_overlap: float = 0.3):
        """
        Initialize temporal consistency checker.
        
        Args:
            max_time_gap: Maximum allowed time gap (seconds)
            min_overlap: Minimum temporal overlap required
        """
        self.max_time_gap = max_time_gap
        self.min_overlap = min_overlap
    
    def compute_temporal_score(self, track1: Dict, track2: Dict) -> float:
        """
        Compute temporal consistency score between two tracks.
        
        Args:
            track1: Track with 'start_time' and 'end_time'
            track2: Track with 'start_time' and 'end_time'
            
        Returns:
            Temporal consistency score (0-1)
        """
        start1 = track1.get('start_time')
        end1 = track1.get('end_time')
        start2 = track2.get('start_time')
        end2 = track2.get('end_time')
        
        if not all([start1, end1, start2, end2]):
            return 0.5
        
        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            # No overlap - check if they're close in time
            time_gap = min(
                abs((start2 - end1).total_seconds()),
                abs((start1 - end2).total_seconds())
            )
            
            if time_gap < self.max_time_gap:
                # Linear decay based on time gap
                score = max(0, 1 - (time_gap / self.max_time_gap))
                return float(score)
            else:
                return 0.0
        
        # Calculate overlap duration
        overlap_duration = (overlap_end - overlap_start).total_seconds()
        duration1 = (end1 - start1).total_seconds()
        duration2 = (end2 - start2).total_seconds()
        
        # Overlap ratio relative to both tracks
        overlap_ratio1 = overlap_duration / duration1 if duration1 > 0 else 0
        overlap_ratio2 = overlap_duration / duration2 if duration2 > 0 else 0
        
        # Combined overlap score
        overlap_score = max(overlap_ratio1, overlap_ratio2)
        
        return float(min(1.0, overlap_score))
    
    def check_consistency(self, observations: List[Dict]) -> float:
        """
        Check temporal consistency of a sequence of observations.
        
        Args:
            observations: List of observations with 'camera_id', 'timestamp'
            
        Returns:
            Consistency score (0-1)
        """
        if len(observations) < 2:
            return 1.0
        
        # Sort by timestamp
        sorted_obs = sorted(observations, key=lambda x: x['timestamp'])
        
        scores = []
        for i in range(len(sorted_obs) - 1):
            current = sorted_obs[i]
            next_obs = sorted_obs[i + 1]
            
            time_gap = (next_obs['timestamp'] - current['timestamp']).total_seconds()
            
            # Check if time gap is reasonable
            if time_gap > self.max_time_gap:
                scores.append(0.0)
            else:
                # Score based on time gap (smaller gap = higher score)
                score = 1 - (time_gap / self.max_time_gap)
                scores.append(max(0.0, score))
        
        return float(np.mean(scores) if scores else 0.5)
    
    def compute_velocity_score(self, positions: List[Tuple[float, float]],
                              timestamps: List[datetime]) -> float:
        """
        Compute velocity consistency score.
        
        Args:
            positions: List of (x, y) positions
            timestamps: List of timestamps
            
        Returns:
            Velocity consistency score (0-1)
        """
        if len(positions) < 2:
            return 0.5
        
        # Calculate velocities
        velocities = []
        for i in range(len(positions) - 1):
            # Position difference
            dx = positions[i+1][0] - positions[i][0]
            dy = positions[i+1][1] - positions[i][1]
            distance = np.sqrt(dx**2 + dy**2)
            
            # Time difference
            dt = (timestamps[i+1] - timestamps[i]).total_seconds()
            if dt > 0:
                velocity = distance / dt
                velocities.append(velocity)
        
        if not velocities:
            return 0.5
        
        # Check velocity consistency (low variance = high consistency)
        mean_velocity = np.mean(velocities)
        std_velocity = np.std(velocities)
        
        # Normalize: CV = std/mean, lower is better
        if mean_velocity > 0:
            cv = std_velocity / mean_velocity
            score = max(0, 1 - cv)
        else:
            score = 0.5
        
        return float(score)