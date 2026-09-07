# behavior/anomaly_detector.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .behavior_analyzer import BehaviorProfile
from .behavior_rules import RuleBasedDetector

class AnomalyDetector:
    """
    Detect anomalous behavior using multiple strategies.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.rule_detector = RuleBasedDetector(config)
        
        # ML-based anomaly detection
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Anomaly thresholds
        self.anomaly_threshold = self.config.get('anomaly_threshold', 0.3)
        self.min_observations = self.config.get('min_observations', 10)
        
        # Historical data for ML
        self.historical_data = []
        self.anomaly_scores = {}
    
    def detect_anomalies(self, current_behavior: Dict,
                        profile: Optional[BehaviorProfile] = None) -> List[Dict]:
        """
        Detect anomalies in current behavior.
        
        Returns:
            List of detected anomalies with details
        """
        anomalies = []
        
        # 1. Rule-based detection
        rule_anomalies = self.rule_detector.detect_anomalies(current_behavior, profile)
        anomalies.extend(rule_anomalies)
        
        # 2. Statistical anomaly detection (if profile exists)
        if profile:
            stat_anomalies = self._detect_statistical_anomalies(current_behavior, profile)
            anomalies.extend(stat_anomalies)
        
        # 3. ML-based anomaly detection (if trained)
        if self.is_trained:
            ml_anomalies = self._detect_ml_anomalies(current_behavior)
            anomalies.extend(ml_anomalies)
        
        return anomalies
    
    def _detect_statistical_anomalies(self, current_behavior: Dict,
                                     profile: BehaviorProfile) -> List[Dict]:
        """Detect anomalies using statistical methods."""
        anomalies = []
        
        # 1. Unusual time (outside normal hours)
        current_hour = datetime.now().hour
        if profile.preferred_hours and current_hour not in profile.preferred_hours:
            if current_hour < 6 or current_hour > 22:  # Late night / early morning
                anomalies.append({
                    'type': 'unusual_time',
                    'severity': 'high',
                    'description': f'Activity at unusual hour: {current_hour}:00',
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat()
                })
        
        # 2. Unusual camera (not in preferences)
        current_camera = current_behavior.get('camera_id')
        if current_camera is not None and profile.camera_preferences:
            if current_camera not in profile.camera_preferences:
                anomalies.append({
                    'type': 'unusual_camera',
                    'severity': 'medium',
                    'description': f'Person visited unusual camera: {current_camera}',
                    'confidence': 0.7,
                    'timestamp': datetime.now().isoformat()
                })
        
        # 3. Unusually long dwell time
        dwell_time = current_behavior.get('dwell_time', 0)
        if dwell_time > 0 and profile.typical_duration > 0:
            if dwell_time > profile.typical_duration * 3:
                anomalies.append({
                    'type': 'abnormal_dwell',
                    'severity': 'medium',
                    'description': f'Unusually long dwell: {dwell_time:.1f}s '
                                  f'(typical: {profile.typical_duration:.1f}s)',
                    'confidence': 0.75,
                    'timestamp': datetime.now().isoformat()
                })
        
        # 4. Unusual transition
        if current_behavior.get('transition'):
            transition = current_behavior['transition']
            key = (transition['from'], transition['to'])
            if key in profile.transition_patterns:
                prob = profile.transition_patterns[key]
                if prob < 0.1:  # Low probability transition
                    anomalies.append({
                        'type': 'unusual_transition',
                        'severity': 'medium',
                        'description': f'Unusual transition: {key[0]} → {key[1]} '
                                      f'(prob: {prob:.2f})',
                        'confidence': 0.7,
                        'timestamp': datetime.now().isoformat()
                    })
        
        # 5. Abnormal visit frequency
        if current_behavior.get('visit_count', 0) > 0:
            expected_frequency = profile.visit_frequency
            if expected_frequency > 0:
                current_frequency = current_behavior['visit_count'] / 24  # per hour
                if current_frequency > expected_frequency * 2:
                    anomalies.append({
                        'type': 'abnormal_frequency',
                        'severity': 'low',
                        'description': f'High visit frequency: {current_frequency:.2f}/h '
                                      f'(normal: {expected_frequency:.2f}/h)',
                        'confidence': 0.6,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return anomalies
    
    def _detect_ml_anomalies(self, current_behavior: Dict) -> List[Dict]:
        """Detect anomalies using Isolation Forest."""
        if not self.is_trained or not self.isolation_forest:
            return []
        
        # Extract features
        features = self._extract_features(current_behavior)
        
        if features is None:
            return []
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Predict anomaly
        anomaly_score = self.isolation_forest.score_samples(features_scaled)[0]
        anomaly_score = 1 - (anomaly_score / -0.5)  # Normalize to [0, 1]
        
        if anomaly_score > self.anomaly_threshold:
            return [{
                'type': 'ml_anomaly',
                'severity': 'high' if anomaly_score > 0.7 else 'medium',
                'description': f'ML-based anomaly detected (score: {anomaly_score:.2f})',
                'confidence': float(anomaly_score),
                'timestamp': datetime.now().isoformat()
            }]
        
        return []
    
    def train_ml_model(self, behavior_data: List[Dict]):
        """
        Train Isolation Forest model on behavioral data.
        """
        if len(behavior_data) < self.min_observations:
            print(f"⚠️ Not enough data for ML training: {len(behavior_data)} < {self.min_observations}")
            return
        
        # Extract features
        features = []
        for data in behavior_data:
            feat = self._extract_features(data)
            if feat is not None:
                features.append(feat)
        
        if len(features) < self.min_observations:
            print(f"⚠️ Not enough valid features: {len(features)}")
            return
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Train Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.isolation_forest.fit(features_scaled)
        self.is_trained = True
        
        print(f"✅ ML model trained on {len(features)} samples")
    
    def _extract_features(self, behavior: Dict) -> Optional[List[float]]:
        """Extract features for ML model."""
        features = []
        
        # 1. Hour of day (converted to sin/cos for circular)
        hour = datetime.now().hour
        features.append(np.sin(2 * np.pi * hour / 24))
        features.append(np.cos(2 * np.pi * hour / 24))
        
        # 2. Day of week
        day = datetime.now().weekday()
        features.append(np.sin(2 * np.pi * day / 7))
        features.append(np.cos(2 * np.pi * day / 7))
        
        # 3. Dwell time
        dwell_time = behavior.get('dwell_time', 0)
        features.append(min(1.0, dwell_time / 3600))  # Normalize to 1 hour
        
        # 4. Number of visits
        visit_count = behavior.get('visit_count', 0)
        features.append(min(1.0, visit_count / 10))  # Normalize to 10 visits
        
        # 5. Camera transitions
        transitions = behavior.get('transitions', [])
        features.append(len(transitions))
        
        # 6. Confidence
        confidence = behavior.get('confidence', 0.5)
        features.append(confidence)
        
        return features
    
    def get_anomaly_score(self, global_id: str) -> float:
        """Get overall anomaly score for a person."""
        return self.anomaly_scores.get(global_id, 0.0)
    
    def update_anomaly_score(self, global_id: str, score: float):
        """Update anomaly score for a person."""
        # Exponential moving average
        if global_id in self.anomaly_scores:
            self.anomaly_scores[global_id] = 0.7 * self.anomaly_scores[global_id] + 0.3 * score
        else:
            self.anomaly_scores[global_id] = score