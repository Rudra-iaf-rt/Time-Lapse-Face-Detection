# behavior/anomaly_scorer.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict

class AnomalyScorer:
    """
    Score and prioritize detected anomalies based on multiple factors.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Score weights
        self.weights = {
            'severity': self.config.get('severity_weight', 0.35),
            'confidence': self.config.get('confidence_weight', 0.25),
            'frequency': self.config.get('frequency_weight', 0.15),
            'recency': self.config.get('recency_weight', 0.15),
            'impact': self.config.get('impact_weight', 0.10)
        }
        
        # Severity scores
        self.severity_scores = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3,
            'info': 0.1
        }
        
        # Anomaly type base scores
        self.type_base_scores = {
            'restricted_zone_entry': 0.9,
            'after_hours_presence': 0.7,
            'excessive_dwell': 0.6,
            'rapid_transition': 0.5,
            'unusual_route': 0.5,
            'capacity_exceeded': 0.8,
            'repeated_visit': 0.4,
            'unusual_time': 0.6,
            'unusual_camera': 0.5,
            'abnormal_dwell': 0.6,
            'unusual_transition': 0.5,
            'abnormal_frequency': 0.4,
            'ml_anomaly': 0.7
        }
        
        # Historical anomaly scores for trend analysis
        self.historical_scores: Dict[str, List[float]] = defaultdict(list)
        self.score_history_window = self.config.get('score_history_window', 100)
        
    def score_anomaly(self, anomaly: Dict, 
                      context: Optional[Dict] = None) -> Dict:
        """
        Score a single anomaly.
        
        Args:
            anomaly: Anomaly dictionary with type, severity, confidence, etc.
            context: Optional context (person history, camera info, etc.)
            
        Returns:
            Enhanced anomaly with score and priority
        """
        # Base score from anomaly type
        anomaly_type = anomaly.get('type', 'unknown')
        base_score = self.type_base_scores.get(anomaly_type, 0.5)
        
        # Severity score
        severity = anomaly.get('severity', 'medium')
        severity_score = self.severity_scores.get(severity, 0.5)
        
        # Confidence score
        confidence = anomaly.get('confidence', 0.5)
        
        # Frequency score (how often this type occurs)
        frequency_score = self._compute_frequency_score(anomaly, context)
        
        # Recency score (recent anomalies are more important)
        recency_score = self._compute_recency_score(anomaly)
        
        # Impact score (potential impact of this anomaly)
        impact_score = self._compute_impact_score(anomaly, context)
        
        # Compute weighted score
        weighted_score = (
            base_score * self.weights['severity'] +
            severity_score * self.weights['severity'] +
            confidence * self.weights['confidence'] +
            frequency_score * self.weights['frequency'] +
            recency_score * self.weights['recency'] +
            impact_score * self.weights['impact']
        )
        
        # Normalize to [0, 1]
        total_weight = sum(self.weights.values())
        final_score = weighted_score / total_weight
        
        # Determine priority level
        priority = self._determine_priority(final_score)
        
        # Update historical scores
        anomaly_key = f"{anomaly.get('global_id', 'unknown')}_{anomaly_type}"
        self.historical_scores[anomaly_key].append(final_score)
        if len(self.historical_scores[anomaly_key]) > self.score_history_window:
            self.historical_scores[anomaly_key] = self.historical_scores[anomaly_key][-self.score_history_window:]
        
        # Return enhanced anomaly
        return {
            **anomaly,
            'score': float(final_score),
            'priority': priority,
            'score_components': {
                'base_score': float(base_score),
                'severity_score': float(severity_score),
                'confidence_score': float(confidence),
                'frequency_score': float(frequency_score),
                'recency_score': float(recency_score),
                'impact_score': float(impact_score)
            },
            'score_timestamp': datetime.now().isoformat()
        }
    
    def score_anomalies(self, anomalies: List[Dict],
                        context: Optional[Dict] = None) -> List[Dict]:
        """
        Score multiple anomalies and sort by priority.
        
        Returns:
            List of scored anomalies sorted by score (highest first)
        """
        scored = [self.score_anomaly(a, context) for a in anomalies]
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        return scored
    
    def _compute_frequency_score(self, anomaly: Dict,
                                context: Optional[Dict]) -> float:
        """
        Compute frequency score based on how often this type occurs.
        """
        anomaly_type = anomaly.get('type', 'unknown')
        global_id = anomaly.get('global_id', 'unknown')
        
        if context and 'recent_anomalies' in context:
            recent = context['recent_anomalies']
            
            # Count occurrences of this type for this person
            count = sum(1 for a in recent 
                       if a.get('type') == anomaly_type and 
                       a.get('global_id') == global_id)
            
            # Higher frequency = higher score (if unusual)
            # But if it's too frequent, it might be normal
            if count == 0:
                return 1.0  # First occurrence is highly unusual
            elif count < 3:
                return 0.8
            elif count < 5:
                return 0.5
            else:
                return 0.3  # Frequent = less unusual
        else:
            # Check historical data
            key = f"{global_id}_{anomaly_type}"
            history = self.historical_scores.get(key, [])
            
            if not history:
                return 0.8  # No history = unusual
            
            # Normalize frequency relative to history
            mean = np.mean(history) if history else 0.5
            std = np.std(history) if history else 0.2
            
            # Z-score approach
            base_score = 0.7  # Default
            if std > 0:
                # More unusual if it deviates from historical mean
                deviation = abs(base_score - mean) / std
                frequency_score = min(1.0, deviation / 3)  # Cap at 3 std dev
                return frequency_score
            else:
                return 0.5
        
        return 0.5
    
    def _compute_recency_score(self, anomaly: Dict) -> float:
        """
        Compute recency score - more recent anomalies score higher.
        """
        timestamp = anomaly.get('timestamp')
        
        if not timestamp:
            return 0.5
        
        # Parse timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                return 0.5
        
        if isinstance(timestamp, datetime):
            # Calculate age in seconds
            age = (datetime.now() - timestamp).total_seconds()
            
            # Exponential decay: newer = higher score
            # Half-life of 1 hour
            half_life = 3600  # 1 hour in seconds
            recency_score = np.exp(-age / half_life)
            
            return float(max(0, recency_score))
        
        return 0.5
    
    def _compute_impact_score(self, anomaly: Dict,
                             context: Optional[Dict]) -> float:
        """
        Compute potential impact of the anomaly.
        """
        anomaly_type = anomaly.get('type', 'unknown')
        
        # Base impact by type
        impact_by_type = {
            'restricted_zone_entry': 0.9,
            'capacity_exceeded': 0.8,
            'after_hours_presence': 0.7,
            'excessive_dwell': 0.6,
            'ml_anomaly': 0.6,
            'rapid_transition': 0.5,
            'unusual_route': 0.5,
            'unusual_camera': 0.4,
            'abnormal_dwell': 0.4,
            'unusual_transition': 0.4,
            'repeated_visit': 0.3,
            'unusual_time': 0.3,
            'abnormal_frequency': 0.3
        }
        
        base_impact = impact_by_type.get(anomaly_type, 0.5)
        
        # Adjust based on context
        if context:
            # Time of day impact
            hour = datetime.now().hour
            if hour < 6 or hour > 22:  # Late night
                base_impact *= 1.2
            
            # Camera importance
            camera_id = anomaly.get('camera_id')
            if camera_id and 'camera_importance' in context:
                importance = context['camera_importance'].get(camera_id, 0.5)
                base_impact = (base_impact + importance) / 2
            
            # Person history impact
            global_id = anomaly.get('global_id')
            if global_id and 'person_history' in context:
                history = context['person_history'].get(global_id, {})
                prior_anomalies = history.get('anomaly_count', 0)
                if prior_anomalies > 5:
                    base_impact *= 1.1  # Repeat offender
                elif prior_anomalies > 10:
                    base_impact *= 1.2
        
        return min(1.0, base_impact)
    
    def _determine_priority(self, score: float) -> str:
        """
        Determine priority level based on score.
        """
        if score >= 0.8:
            return 'critical'
        elif score >= 0.6:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        elif score >= 0.2:
            return 'low'
        else:
            return 'info'
    
    def get_anomaly_trend(self, global_id: str, 
                          anomaly_type: str,
                          window_days: int = 7) -> Dict:
        """
        Get trend analysis for an anomaly type.
        """
        key = f"{global_id}_{anomaly_type}"
        scores = self.historical_scores.get(key, [])
        
        if not scores:
            return {
                'total_occurrences': 0,
                'trend': 'stable',
                'avg_score': 0,
                'latest_score': 0
            }
        
        # Calculate trend
        recent_scores = scores[-self.score_history_window:]
        
        if len(recent_scores) >= 3:
            # Simple linear regression for trend
            x = np.arange(len(recent_scores))
            y = np.array(recent_scores)
            
            slope = np.polyfit(x, y, 1)[0]
            
            if slope > 0.05:
                trend = 'increasing'
            elif slope < -0.05:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'total_occurrences': len(scores),
            'trend': trend,
            'avg_score': float(np.mean(recent_scores)),
            'max_score': float(np.max(recent_scores)),
            'min_score': float(np.min(recent_scores)),
            'latest_score': float(scores[-1]) if scores else 0
        }
    
    def get_priority_summary(self, anomalies: List[Dict]) -> Dict:
        """
        Get summary of anomaly priorities.
        """
        summary = {
            'total': len(anomalies),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0,
            'by_type': defaultdict(lambda: {'count': 0, 'severity': 'low'}),
            'top_anomalies': []
        }
        
        for anomaly in anomalies:
            # Count by priority
            priority = anomaly.get('priority', 'low')
            summary[priority] = summary.get(priority, 0) + 1
            
            # Count by type
            anomaly_type = anomaly.get('type', 'unknown')
            summary['by_type'][anomaly_type]['count'] += 1
            
            # Track max severity for each type
            if anomaly.get('severity') == 'high' or anomaly.get('severity') == 'critical':
                summary['by_type'][anomaly_type]['severity'] = anomaly.get('severity')
        
        # Get top anomalies
        sorted_anomalies = sorted(anomalies, 
                                  key=lambda x: x.get('score', 0), 
                                  reverse=True)
        summary['top_anomalies'] = sorted_anomalies[:5]
        
        return dict(summary)
    
    def get_risk_score(self, global_id: str, 
                       anomalies: List[Dict]) -> Dict:
        """
        Compute overall risk score for a person.
        """
        if not anomalies:
            return {
                'global_id': global_id,
                'risk_score': 0,
                'anomaly_count': 0,
                'max_severity': 'none'
            }
        
        # Score each anomaly
        scored = self.score_anomalies(anomalies)
        
        # Aggregate scores
        scores = [a['score'] for a in scored]
        
        # Calculate risk score (weighted average with recency)
        weights = []
        for a in scored:
            recency = self._compute_recency_score(a)
            weights.append(1 + recency * 2)  # Give more weight to recent anomalies
        
        weighted_avg = np.average(scores, weights=weights) if weights else 0
        
        # Determine max severity
        max_severity = 'none'
        severity_order = ['info', 'low', 'medium', 'high', 'critical']
        for anomaly in scored:
            severity = anomaly.get('severity', 'low')
            if severity_order.index(severity) > severity_order.index(max_severity):
                max_severity = severity
        
        return {
            'global_id': global_id,
            'risk_score': float(min(1.0, weighted_avg * 1.5)),
            'anomaly_count': len(anomalies),
            'max_severity': max_severity,
            'anomaly_types': [a['type'] for a in scored],
            'recent_score': float(scored[0]['score']) if scored else 0
        }
    
    def get_recommendations(self, anomaly: Dict) -> List[str]:
        """
        Get recommendations based on anomaly type.
        """
        anomaly_type = anomaly.get('type', 'unknown')
        recommendations = {
            'restricted_zone_entry': [
                'Send security alert immediately',
                'Check person authorization status',
                'Review video footage of entry',
                'Log incident for compliance'
            ],
            'after_hours_presence': [
                'Check if person has after-hours access',
                'Notify security personnel',
                'Review camera footage for after-hours activity',
                'Check access logs for this person'
            ],
            'excessive_dwell': [
                'Investigate reason for extended stay',
                'Check if person is waiting for someone',
                'Review camera footage for unusual activity',
                'Monitor for further anomalies'
            ],
            'rapid_transition': [
                'Check if person is being followed',
                'Review movement pattern',
                'Monitor for suspicious behavior',
                'Check for potential tailgating'
            ],
            'unusual_route': [
                'Verify if person is lost or confused',
                'Check if they re avoiding specific areas',
                'Review alternative routes',
                'Monitor navigation behavior'
            ],
            'capacity_exceeded': [
                'Monitor crowd density',
                'Consider activating crowd control measures',
                'Alert safety personnel',
                'Prepare for potential evacuation if needed'
            ],
            'unusual_time': [
                'Check if scheduled appointment exists',
                'Verify after-hours authorization',
                'Review access control logs',
                'Monitor for continued unusual timing'
            ],
            'unusual_camera': [
                'Check if person has legitimate reason to be there',
                'Review access permissions',
                'Monitor for continued wandering',
                'Verify identity'
            ],
            'abnormal_dwell': [
                'Investigate reason for extended presence',
                'Check if person is waiting for someone/event',
                'Review video for unusual behavior',
                'Monitor for further anomalies'
            ],
            'ml_anomaly': [
                'Review recent behavior changes',
                'Check for pattern shift',
                'Compare against historical behavior',
                'Investigate potential explanation'
            ]
        }
        
        return recommendations.get(anomaly_type, [
            'Investigate anomaly further',
            'Monitor for additional anomalies',
            'Review relevant camera footage',
            'Document observation'
        ])
    
    def export_risk_report(self, all_anomalies: Dict[str, List[Dict]],
                          export_path: str) -> Dict:
        """
        Export a comprehensive risk report.
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_persons': len(all_anomalies),
            'persons_with_anomalies': 0,
            'total_anomalies': sum(len(a) for a in all_anomalies.values()),
            'risk_summary': {},
            'top_risk_persons': [],
            'anomaly_type_distribution': defaultdict(int),
            'priority_distribution': defaultdict(int)
        }
        
        # Analyze each person
        for global_id, anomalies in all_anomalies.items():
            if anomalies:
                report['persons_with_anomalies'] += 1
                
                # Get risk score
                risk = self.get_risk_score(global_id, anomalies)
                report['risk_summary'][global_id] = risk
                
                # Count anomaly types
                for anomaly in anomalies:
                    report['anomaly_type_distribution'][anomaly.get('type', 'unknown')] += 1
                    
                    # Score anomaly for priority
                    scored = self.score_anomaly(anomaly)
                    report['priority_distribution'][scored['priority']] += 1
        
        # Sort by risk score
        sorted_persons = sorted(
            report['risk_summary'].items(),
            key=lambda x: x[1]['risk_score'],
            reverse=True
        )
        
        report['top_risk_persons'] = [
            {
                'global_id': pid,
                'risk_score': data['risk_score'],
                'anomaly_count': data['anomaly_count'],
                'max_severity': data['max_severity']
            }
            for pid, data in sorted_persons[:10]
        ]
        
        # Convert to regular dict for JSON
        report['anomaly_type_distribution'] = dict(report['anomaly_type_distribution'])
        report['priority_distribution'] = dict(report['priority_distribution'])
        
        # Save report
        import json
        with open(export_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Risk report exported to {export_path}")
        
        return report