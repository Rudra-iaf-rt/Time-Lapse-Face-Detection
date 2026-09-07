# crowd/crowd_analyzer.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class CrowdMetrics:
    """Crowd metrics for a time period."""
    timestamp: datetime
    camera_id: int
    occupancy: int
    capacity: int
    occupancy_percentage: float
    entry_rate: float  # people per minute
    exit_rate: float   # people per minute
    dwell_time_avg: float  # average dwell time in seconds
    crowd_density: float  # people per square meter
    flow_rate: float  # people per minute passing through
    congestion_level: str  # 'low', 'medium', 'high', 'critical'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'camera_id': self.camera_id,
            'occupancy': self.occupancy,
            'capacity': self.capacity,
            'occupancy_percentage': self.occupancy_percentage,
            'entry_rate': self.entry_rate,
            'exit_rate': self.exit_rate,
            'dwell_time_avg': self.dwell_time_avg,
            'crowd_density': self.crowd_density,
            'flow_rate': self.flow_rate,
            'congestion_level': self.congestion_level
        }

@dataclass
class CrowdTrend:
    """Crowd trend over time."""
    camera_id: int
    period: str  # 'hourly', 'daily', 'weekly'
    data: Dict[str, float]
    peak_time: str
    peak_occupancy: int
    average_occupancy: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'

class CrowdAnalyzer:
    """
    Analyze crowd metrics and patterns.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.camera_capacities = self.config.get('camera_capacities', {})
        self.occupancy_thresholds = {
            'low': self.config.get('low_threshold', 0.3),
            'medium': self.config.get('medium_threshold', 0.6),
            'high': self.config.get('high_threshold', 0.8),
            'critical': self.config.get('critical_threshold', 0.95)
        }
        self.metrics_history: List[CrowdMetrics] = []
        self.max_history = self.config.get('max_history', 10000)
    
    def analyze_crowd(self, camera_id: int, 
                      persons: List[Dict],
                      timestamp: datetime) -> CrowdMetrics:
        """
        Analyze crowd for a camera at a given time.
        
        Args:
            camera_id: Camera identifier
            persons: List of person detections
            timestamp: Current timestamp
            
        Returns:
            CrowdMetrics object
        """
        # Current occupancy
        occupancy = len(persons)
        capacity = self.camera_capacities.get(camera_id, 100)
        occupancy_percentage = occupancy / capacity if capacity > 0 else 0
        
        # Entry/Exit rates (based on recent history)
        entry_rate, exit_rate = self._compute_flow_rates(camera_id, persons)
        
        # Average dwell time
        dwell_times = [p.get('dwell_time', 0) for p in persons if p.get('dwell_time', 0) > 0]
        avg_dwell = np.mean(dwell_times) if dwell_times else 0
        
        # Crowd density (assuming known area)
        area = self.config.get('camera_areas', {}).get(camera_id, 100)  # square meters
        density = occupancy / area if area > 0 else 0
        
        # Flow rate
        flow_rate = self._compute_flow_rate(camera_id, timestamp)
        
        # Congestion level
        congestion = self._get_congestion_level(occupancy_percentage)
        
        metrics = CrowdMetrics(
            timestamp=timestamp,
            camera_id=camera_id,
            occupancy=occupancy,
            capacity=capacity,
            occupancy_percentage=occupancy_percentage,
            entry_rate=entry_rate,
            exit_rate=exit_rate,
            dwell_time_avg=avg_dwell,
            crowd_density=density,
            flow_rate=flow_rate,
            congestion_level=congestion
        )
        
        # Store in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        return metrics
    
    def _compute_flow_rates(self, camera_id: int, 
                           persons: List[Dict]) -> Tuple[float, float]:
        """Compute entry and exit rates."""
        # In real implementation, track person movements
        # For now, estimate from recent history
        
        if not self.metrics_history:
            return 0.0, 0.0
        
        # Get recent metrics for this camera
        recent = [m for m in self.metrics_history[-10:] 
                 if m.camera_id == camera_id]
        
        if not recent:
            return 0.0, 0.0
        
        # Calculate rate of change
        if len(recent) >= 2:
            occupancy_changes = []
            for i in range(1, len(recent)):
                diff = recent[i].occupancy - recent[i-1].occupancy
                time_diff = (recent[i].timestamp - recent[i-1].timestamp).total_seconds() / 60
                if time_diff > 0:
                    occupancy_changes.append(diff / time_diff)
            
            if occupancy_changes:
                # Positive changes = entries, negative = exits
                entry_rate = max(0, np.mean([c for c in occupancy_changes if c > 0]))
                exit_rate = max(0, -np.mean([c for c in occupancy_changes if c < 0]))
                return entry_rate, exit_rate
        
        return 0.0, 0.0
    
    def _compute_flow_rate(self, camera_id: int, 
                          timestamp: datetime) -> float:
        """Compute flow rate (people passing through)."""
        # Track transitions in/out
        # Simplified: use recent changes in occupancy
        
        recent = [m for m in self.metrics_history[-5:] 
                 if m.camera_id == camera_id]
        
        if len(recent) < 2:
            return 0.0
        
        # Calculate absolute changes
        total_changes = 0
        total_time = 0
        
        for i in range(1, len(recent)):
            diff = abs(recent[i].occupancy - recent[i-1].occupancy)
            time_diff = (recent[i].timestamp - recent[i-1].timestamp).total_seconds() / 60
            if time_diff > 0:
                total_changes += diff
                total_time += time_diff
        
        return total_changes / total_time if total_time > 0 else 0
    
    def _get_congestion_level(self, occupancy_percentage: float) -> str:
        """Determine congestion level from occupancy percentage."""
        if occupancy_percentage >= self.occupancy_thresholds['critical']:
            return 'critical'
        elif occupancy_percentage >= self.occupancy_thresholds['high']:
            return 'high'
        elif occupancy_percentage >= self.occupancy_thresholds['medium']:
            return 'medium'
        elif occupancy_percentage >= self.occupancy_thresholds['low']:
            return 'low'
        else:
            return 'very_low'
    
    def get_crowd_trends(self, camera_id: int, 
                         period: str = 'hourly') -> CrowdTrend:
        """
        Get crowd trends for a camera over time.
        """
        # Filter metrics for this camera
        camera_metrics = [m for m in self.metrics_history 
                         if m.camera_id == camera_id]
        
        if not camera_metrics:
            return CrowdTrend(
                camera_id=camera_id,
                period=period,
                data={},
                peak_time='',
                peak_occupancy=0,
                average_occupancy=0,
                trend_direction='stable'
            )
        
        # Group by period
        grouped_data = defaultdict(list)
        
        for metric in camera_metrics:
            if period == 'hourly':
                key = metric.timestamp.strftime('%Y-%m-%d %H:00')
            elif period == 'daily':
                key = metric.timestamp.strftime('%Y-%m-%d')
            elif period == 'weekly':
                key = f"Week {metric.timestamp.isocalendar()[1]}"
            else:
                key = metric.timestamp.strftime('%Y-%m-%d %H:00')
            
            grouped_data[key].append(metric.occupancy)
        
        # Compute averages
        trend_data = {}
        for key, values in grouped_data.items():
            trend_data[key] = np.mean(values)
        
        # Find peak
        peak_time = max(trend_data.items(), key=lambda x: x[1])[0] if trend_data else ''
        peak_occupancy = max(trend_data.values()) if trend_data else 0
        
        # Compute average
        avg_occupancy = np.mean(list(trend_data.values())) if trend_data else 0
        
        # Determine trend direction
        if len(trend_data) >= 3:
            values = list(trend_data.values())
            # Simple linear regression
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0]
            
            if slope > 0.05:
                direction = 'increasing'
            elif slope < -0.05:
                direction = 'decreasing'
            else:
                direction = 'stable'
        else:
            direction = 'stable'
        
        return CrowdTrend(
            camera_id=camera_id,
            period=period,
            data=trend_data,
            peak_time=peak_time,
            peak_occupancy=peak_occupancy,
            average_occupancy=avg_occupancy,
            trend_direction=direction
        )
    
    def get_hotspots(self, time_range: Tuple[datetime, datetime]) -> List[Dict]:
        """
        Identify crowd hotspots in a time range.
        """
        start_time, end_time = time_range
        
        # Filter metrics in time range
        metrics = [m for m in self.metrics_history 
                  if start_time <= m.timestamp <= end_time]
        
        if not metrics:
            return []
        
        # Group by camera
        camera_metrics = defaultdict(list)
        for metric in metrics:
            camera_metrics[metric.camera_id].append(metric)
        
        # Analyze each camera
        hotspots = []
        for camera_id, camera_metrics_list in camera_metrics.items():
            # Average occupancy
            avg_occupancy = np.mean([m.occupancy for m in camera_metrics_list])
            max_occupancy = max([m.occupancy for m in camera_metrics_list])
            
            # Peak time
            peak_time = max(camera_metrics_list, key=lambda m: m.occupancy).timestamp
            
            # Capacity utilization
            capacity = self.camera_capacities.get(camera_id, 100)
            utilization = avg_occupancy / capacity if capacity > 0 else 0
            
            # Congestion level
            congestion = self._get_congestion_level(utilization)
            
            if utilization > 0.5:  # Only include busy areas
                hotspots.append({
                    'camera_id': camera_id,
                    'avg_occupancy': avg_occupancy,
                    'max_occupancy': max_occupancy,
                    'peak_time': peak_time.isoformat(),
                    'utilization': utilization,
                    'congestion': congestion,
                    'density': np.mean([m.crowd_density for m in camera_metrics_list])
                })
        
        # Sort by utilization
        hotspots.sort(key=lambda x: x['utilization'], reverse=True)
        
        return hotspots
    
    def get_peak_hours(self, camera_id: int, 
                       days: int = 7) -> Dict[int, float]:
        """
        Get peak hours for a camera over N days.
        """
        # Filter recent metrics
        cutoff = datetime.now() - timedelta(days=days)
        metrics = [m for m in self.metrics_history 
                  if m.camera_id == camera_id and m.timestamp >= cutoff]
        
        if not metrics:
            return {}
        
        # Group by hour
        hourly_occupancy = defaultdict(list)
        for metric in metrics:
            hour = metric.timestamp.hour
            hourly_occupancy[hour].append(metric.occupancy)
        
        # Compute averages
        peak_hours = {}
        for hour, occupancies in hourly_occupancy.items():
            peak_hours[hour] = np.mean(occupancies)
        
        return dict(peak_hours)