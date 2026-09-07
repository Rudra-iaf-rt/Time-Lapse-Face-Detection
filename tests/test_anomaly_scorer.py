# tests/test_anomaly_scorer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json

from behavior.anomaly_scorer import AnomalyScorer

def test_anomaly_scoring():
    """Test anomaly scoring."""
    print("🧪 Testing anomaly scoring...")
    
    scorer = AnomalyScorer({
        'severity_weight': 0.35,
        'confidence_weight': 0.25,
        'frequency_weight': 0.15,
        'recency_weight': 0.15,
        'impact_weight': 0.10
    })
    
    # Test anomalies
    anomalies = [
        {
            'type': 'restricted_zone_entry',
            'severity': 'high',
            'confidence': 0.9,
            'description': 'Entered restricted zone',
            'timestamp': datetime.now().isoformat(),
            'global_id': 'PERSON_001',
            'camera_id': 4
        },
        {
            'type': 'after_hours_presence',
            'severity': 'medium',
            'confidence': 0.7,
            'description': 'Present after hours',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'global_id': 'PERSON_002',
            'camera_id': 2
        },
        {
            'type': 'excessive_dwell',
            'severity': 'medium',
            'confidence': 0.6,
            'description': 'Long dwell time',
            'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'global_id': 'PERSON_003',
            'camera_id': 1
        },
        {
            'type': 'unusual_time',
            'severity': 'low',
            'confidence': 0.5,
            'description': 'Unusual timing',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
            'global_id': 'PERSON_004',
            'camera_id': 3
        },
        {
            'type': 'ml_anomaly',
            'severity': 'high',
            'confidence': 0.85,
            'description': 'ML detected anomaly',
            'timestamp': datetime.now().isoformat(),
            'global_id': 'PERSON_001',
            'camera_id': 0
        }
    ]
    
    print("\n   Scoring individual anomalies:")
    for anomaly in anomalies:
        scored = scorer.score_anomaly(anomaly)
        print(f"\n   {scored['type']}:")
        print(f"   - Score: {scored['score']:.3f}")
        print(f"   - Priority: {scored['priority']}")
        print(f"   - Confidence: {scored['confidence']}")
        print(f"   - Components: {json.dumps(scored['score_components'], indent=2)}")
    
    # Score all anomalies
    scored_anomalies = scorer.score_anomalies(anomalies)
    
    print("\n   Ranking anomalies:")
    for i, anomaly in enumerate(scored_anomalies, 1):
        print(f"   {i}. {anomaly['type']} - Score: {anomaly['score']:.3f} "
              f"(Priority: {anomaly['priority']})")
    
    return scorer

def test_risk_analysis(scorer):
    """Test risk analysis."""
    print("\n🧪 Testing risk analysis...")
    
    # Group anomalies by person
    anomalies_by_person = {
        'PERSON_001': [
            {
                'type': 'restricted_zone_entry',
                'severity': 'high',
                'confidence': 0.9,
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'ml_anomaly',
                'severity': 'high',
                'confidence': 0.85,
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat()
            }
        ],
        'PERSON_002': [
            {
                'type': 'after_hours_presence',
                'severity': 'medium',
                'confidence': 0.7,
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ],
        'PERSON_003': [
            {
                'type': 'excessive_dwell',
                'severity': 'medium',
                'confidence': 0.6,
                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat()
            },
            {
                'type': 'unusual_route',
                'severity': 'low',
                'confidence': 0.5,
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()
            }
        ]
    }
    
    print("\n   Risk scores per person:")
    for person_id, anomalies in anomalies_by_person.items():
        risk = scorer.get_risk_score(person_id, anomalies)
        print(f"\n   {person_id}:")
        print(f"   - Risk Score: {risk['risk_score']:.3f}")
        print(f"   - Anomaly Count: {risk['anomaly_count']}")
        print(f"   - Max Severity: {risk['max_severity']}")
        print(f"   - Types: {risk['anomaly_types']}")
    
    # Priority summary
    all_anomalies = [a for anomalies in anomalies_by_person.values() for a in anomalies]
    summary = scorer.get_priority_summary(all_anomalies)
    
    print("\n   Priority Summary:")
    print(f"   - Total: {summary['total']}")
    for priority in ['critical', 'high', 'medium', 'low', 'info']:
        if priority in summary:
            print(f"   - {priority}: {summary[priority]}")
    
    return anomalies_by_person

def test_recommendations(scorer):
    """Test recommendations."""
    print("\n🧪 Testing recommendations...")
    
    anomaly_types = [
        'restricted_zone_entry',
        'after_hours_presence',
        'excessive_dwell',
        'rapid_transition',
        'unusual_route',
        'capacity_exceeded',
        'ml_anomaly'
    ]
    
    for anomaly_type in anomaly_types:
        anomaly = {
            'type': anomaly_type,
            'severity': 'high',
            'confidence': 0.8
        }
        
        recommendations = scorer.get_recommendations(anomaly)
        print(f"\n   {anomaly_type}:")
        for rec in recommendations:
            print(f"   - {rec}")

def test_trend_analysis(scorer):
    """Test trend analysis."""
    print("\n🧪 Testing trend analysis...")
    
    # Simulate historical scores
    for i in range(20):
        # Add scores for PERSON_001 restricted_zone_entry
        anomaly = {
            'type': 'restricted_zone_entry',
            'global_id': 'PERSON_001',
            'confidence': 0.7 + np.random.rand() * 0.25,
            'severity': 'high' if np.random.rand() > 0.5 else 'medium',
            'timestamp': (datetime.now() - timedelta(hours=i)).isoformat()
        }
        
        # Score to add to history
        scored = scorer.score_anomaly(anomaly)
    
    # Analyze trend
    trend = scorer.get_anomaly_trend('PERSON_001', 'restricted_zone_entry')
    
    print("\n   Trend Analysis for PERSON_001 - restricted_zone_entry:")
    print(f"   - Total Occurrences: {trend['total_occurrences']}")
    print(f"   - Trend: {trend['trend']}")
    print(f"   - Average Score: {trend['avg_score']:.3f}")
    print(f"   - Latest Score: {trend['latest_score']:.3f}")
    print(f"   - Max Score: {trend['max_score']:.3f}")

def test_export_report(scorer, anomalies_by_person):
    """Test report export."""
    print("\n🧪 Testing report export...")
    
    export_path = "tests/test_results/risk_report.json"
    report = scorer.export_risk_report(anomalies_by_person, export_path)
    
    print("\n   Report Summary:")
    print(f"   - Generated: {report['generated_at']}")
    print(f"   - Total Persons: {report['total_persons']}")
    print(f"   - Persons with Anomalies: {report['persons_with_anomalies']}")
    print(f"   - Total Anomalies: {report['total_anomalies']}")
    
    print("\n   Top Risk Persons:")
    for person in report['top_risk_persons']:
        print(f"   - {person['global_id']}: Risk={person['risk_score']:.3f}, "
              f"Count={person['anomaly_count']}, Severity={person['max_severity']}")
    
    print("\n   Anomaly Type Distribution:")
    for a_type, count in report['anomaly_type_distribution'].items():
        print(f"   - {a_type}: {count}")
    
    return report

def main():
    print("=" * 60)
    print("🧪 Anomaly Scorer Tests")
    print("=" * 60)
    
    # Ensure test directories exist
    os.makedirs("tests/test_results", exist_ok=True)
    
    # Run tests
    scorer = test_anomaly_scoring()
    anomalies_by_person = test_risk_analysis(scorer)
    test_recommendations(scorer)
    test_trend_analysis(scorer)
    test_export_report(scorer, anomalies_by_person)
    
    print("\n" + "=" * 60)
    print("✅ All anomaly scorer tests completed!")

if __name__ == "__main__":
    import numpy as np  # For random in trend test
    main()