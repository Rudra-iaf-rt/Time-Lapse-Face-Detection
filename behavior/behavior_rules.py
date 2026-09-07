# behavior/behavior_rules.py
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class RuleBasedDetector:
    """
    Rule-based anomaly detection.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict]:
        """Load detection rules."""
        rules = [
            {
                'name': 'restricted_zone_entry',
                'type': 'location',
                'severity': 'high',
                'description': 'Person entered restricted zone',
                'cameras': self.config.get('restricted_zones', [])
            },
            {
                'name': 'after_hours_presence',
                'type': 'time',
                'severity': 'medium',
                'description': 'Person present after hours',
                'start_hour': 22,
                'end_hour': 6
            },
            {
                'name': 'excessive_dwell',
                'type': 'duration',
                'severity': 'medium',
                'description': 'Excessive dwell time',
                'threshold': 3600  # 1 hour
            },
            {
                'name': 'rapid_transition',
                'type': 'transition',
                'severity': 'medium',
                'description': 'Rapid camera transition',
                'threshold': 5  # 5 seconds
            },
            {
                'name': 'unusual_route',
                'type': 'route',
                'severity': 'low',
                'description': 'Unusual movement route'
            },
            {
                'name': 'capacity_exceeded',
                'type': 'crowd',
                'severity': 'medium',
                'description': 'Camera capacity exceeded',
                'threshold': 50  # 50 people
            },
            {
                'name': 'repeated_visit',
                'type': 'frequency',
                'severity': 'low',
                'description': 'Repeated visits to same location',
                'threshold': 10  # 10 visits per day
            }
        ]
        return rules
    
    def detect_anomalies(self, current_behavior: Dict,
                        profile: Optional[Any] = None) -> List[Dict]:
        """Detect anomalies based on rules."""
        anomalies = []
        
        for rule in self.rules:
            if rule['type'] == 'location':
                result = self._check_location_rule(current_behavior, rule)
            elif rule['type'] == 'time':
                result = self._check_time_rule(current_behavior, rule)
            elif rule['type'] == 'duration':
                result = self._check_duration_rule(current_behavior, rule)
            elif rule['type'] == 'transition':
                result = self._check_transition_rule(current_behavior, rule)
            elif rule['type'] == 'route':
                result = self._check_route_rule(current_behavior, profile, rule)
            elif rule['type'] == 'crowd':
                result = self._check_crowd_rule(current_behavior, rule)
            elif rule['type'] == 'frequency':
                result = self._check_frequency_rule(current_behavior, rule)
            else:
                continue
            
            if result:
                anomalies.append({
                    'type': rule['name'],
                    'severity': rule['severity'],
                    'description': rule['description'],
                    'details': result,
                    'timestamp': datetime.now().isoformat()
                })
        
        return anomalies
    
    def _check_location_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check if person entered restricted zone."""
        camera_id = behavior.get('camera_id')
        restricted_zones = rule.get('cameras', [])
        
        if camera_id in restricted_zones:
            return {
                'camera': camera_id,
                'zone': restricted_zones[camera_id] if isinstance(restricted_zones, dict) else 'restricted'
            }
        return None
    
    def _check_time_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check if person is active after hours."""
        current_hour = datetime.now().hour
        start_hour = rule.get('start_hour', 22)
        end_hour = rule.get('end_hour', 6)
        
        if current_hour >= start_hour or current_hour < end_hour:
            return {
                'hour': current_hour,
                'expected': f'{start_hour}:00 - {end_hour}:00'
            }
        return None
    
    def _check_duration_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check for excessive dwell time."""
        dwell_time = behavior.get('dwell_time', 0)
        threshold = rule.get('threshold', 3600)
        
        if dwell_time > threshold:
            return {
                'duration': dwell_time,
                'threshold': threshold
            }
        return None
    
    def _check_transition_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check for rapid camera transitions."""
        transitions = behavior.get('transitions', [])
        threshold = rule.get('threshold', 5)
        
        for transition in transitions:
            if transition.get('duration', 0) < threshold:
                return {
                    'from_camera': transition['from'],
                    'to_camera': transition['to'],
                    'duration': transition['duration'],
                    'threshold': threshold
                }
        return None
    
    def _check_route_rule(self, behavior: Dict, profile: Optional[Any],
                         rule: Dict) -> Optional[Dict]:
        """Check for unusual routes."""
        if not profile:
            return None
        
        current_route = behavior.get('route', [])
        typical_route = profile.typical_route if profile else []
        
        if not typical_route:
            return None
        
        # Check if route significantly deviates from typical
        common_cameras = set(current_route) & set(typical_route)
        if len(common_cameras) < len(current_route) * 0.3:
            return {
                'current_route': current_route,
                'typical_route': typical_route,
                'deviation': len(current_route) - len(common_cameras)
            }
        return None
    
    def _check_crowd_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check if camera capacity is exceeded."""
        occupancy = behavior.get('occupancy', 0)
        threshold = rule.get('threshold', 50)
        
        if occupancy > threshold:
            return {
                'occupancy': occupancy,
                'capacity': threshold,
                'excess': occupancy - threshold
            }
        return None
    
    def _check_frequency_rule(self, behavior: Dict, rule: Dict) -> Optional[Dict]:
        """Check for repeated visits."""
        visit_count = behavior.get('visit_count', 0)
        threshold = rule.get('threshold', 10)
        
        if visit_count > threshold:
            return {
                'visits': visit_count,
                'threshold': threshold
            }
        return None