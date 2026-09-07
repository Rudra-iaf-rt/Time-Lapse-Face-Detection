# crowd/occupancy_tracker.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

class OccupancyTracker:
    """
    Track occupancy per camera over time.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.occupancy_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.entry_exit_log = defaultdict(lambda: deque(maxlen=1000))
        self.camera_capacities = self.config.get('camera_capacities', {})
        
    def update_occupancy(self, camera_id: int, 
                         persons: List[Dict],
                         timestamp: datetime):
        """
        Update occupancy for a camera.
        """
        occupancy = len(persons)
        
        # Store in buffer
        self.occupancy_buffer[camera_id].append({
            'timestamp': timestamp,
            'occupancy': occupancy,
            'persons': persons
        })
        
        # Track entries/exits
        if len(self.occupancy_buffer[camera_id]) >= 2:
            prev = self.occupancy_buffer[camera_id][-2]
            current = self.occupancy_buffer[camera_id][-1]
            
            diff = current['occupancy'] - prev['occupancy']
            
            if diff > 0:
                # Entries
                for _ in range(diff):
                    self.entry_exit_log[camera_id].append({
                        'type': 'entry',
                        'timestamp': timestamp,
                        'person': persons[_] if _ < len(persons) else None
                    })
            elif diff < 0:
                # Exits
                for _ in range(abs(diff)):
                    self.entry_exit_log[camera_id].append({
                        'type': 'exit',
                        'timestamp': timestamp,
                        'person': None
                    })
    
    def get_current_occupancy(self, camera_id: int) -> int:
        """Get current occupancy for a camera."""
        if camera_id not in self.occupancy_buffer:
            return 0
        
        if not self.occupancy_buffer[camera_id]:
            return 0
        
        return self.occupancy_buffer[camera_id][-1]['occupancy']
    
    def get_occupancy_history(self, camera_id: int, 
                              window_seconds: int = 300) -> List[Dict]:
        """
        Get occupancy history for a camera within a time window.
        """
        if camera_id not in self.occupancy_buffer:
            return []
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        
        history = []
        for entry in self.occupancy_buffer[camera_id]:
            if entry['timestamp'] >= cutoff:
                history.append(entry)
        
        return history
    
    def get_occupancy_stats(self, camera_id: int, 
                           window_seconds: int = 3600) -> Dict:
        """
        Get occupancy statistics for a camera.
        """
        history = self.get_occupancy_history(camera_id, window_seconds)
        
        if not history:
            return {
                'current': 0,
                'avg': 0,
                'max': 0,
                'min': 0,
                'std': 0,
                'samples': 0
            }
        
        occupancies = [entry['occupancy'] for entry in history]
        
        return {
            'current': occupancies[-1] if occupancies else 0,
            'avg': np.mean(occupancies),
            'max': max(occupancies),
            'min': min(occupancies),
            'std': np.std(occupancies),
            'samples': len(occupancies)
        }
    
    def get_capacity_utilization(self, camera_id: int) -> float:
        """
        Get capacity utilization for a camera.
        """
        current = self.get_current_occupancy(camera_id)
        capacity = self.camera_capacities.get(camera_id, 100)
        
        return current / capacity if capacity > 0 else 0
    
    def get_alerts(self, camera_id: int, 
                   threshold: float = 0.85) -> List[Dict]:
        """
        Get occupancy alerts for a camera.
        """
        alerts = []
        
        current = self.get_current_occupancy(camera_id)
        capacity = self.camera_capacities.get(camera_id, 100)
        
        if capacity > 0 and current / capacity >= threshold:
            alerts.append({
                'camera_id': camera_id,
                'occupancy': current,
                'capacity': capacity,
                'utilization': current / capacity,
                'timestamp': datetime.now().isoformat(),
                'severity': 'high' if current / capacity >= 0.95 else 'medium',
                'message': f'Occupancy exceeded threshold: {current}/{capacity}'
            })
        
        return alerts
    
    def get_entry_exit_rate(self, camera_id: int, 
                           window_seconds: int = 300) -> Tuple[float, float]:
        """
        Get entry and exit rates for a camera.
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        
        entries = 0
        exits = 0
        
        for log in self.entry_exit_log.get(camera_id, []):
            if log['timestamp'] >= cutoff:
                if log['type'] == 'entry':
                    entries += 1
                else:
                    exits += 1
        
        rate_window = window_seconds / 60  # minutes
        entry_rate = entries / rate_window if rate_window > 0 else 0
        exit_rate = exits / rate_window if rate_window > 0 else 0
        
        return entry_rate, exit_rate