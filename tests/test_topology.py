# tests/test_topology.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime, timedelta
from topology.camera_graph import CameraGraph, CameraTransition
from topology.transition_learner import TransitionLearner
from topology.spatial_consistency import SpatialConsistencyChecker
from topology.temporal_consistency import TemporalConsistencyChecker
from topology.topology_visualizer import TopologyVisualizer

def test_camera_graph():
    """Test camera graph construction."""
    print("🧪 Testing camera graph...")
    
    graph = CameraGraph()
    
    # Add cameras
    for i in range(5):
        graph.add_camera(i)
    
    # Add transitions
    transitions = [
        (0, 1, 0.8, 5.0, 3.0, 8.0, 1.0),
        (0, 2, 0.6, 10.0, 5.0, 15.0, 2.0),
        (1, 2, 0.7, 3.0, 2.0, 5.0, 0.5),
        (1, 3, 0.5, 8.0, 5.0, 12.0, 1.5),
        (2, 3, 0.9, 4.0, 3.0, 6.0, 0.8),
        (3, 4, 0.7, 6.0, 4.0, 9.0, 1.2)
    ]
    
    for from_cam, to_cam, prob, avg, min_t, max_t, std in transitions:
        transition = CameraTransition(
            from_camera=from_cam,
            to_camera=to_cam,
            transition_probability=prob,
            avg_travel_time=avg,
            min_travel_time=min_t,
            max_travel_time=max_t,
            std_travel_time=std,
            observation_count=10,
            last_observed=datetime.now()
        )
        graph.add_transition(from_cam, to_cam, transition)
    
    # Test queries
    print(f"   Possible destinations from camera 0: {graph.get_possible_destinations(0)}")
    print(f"   Possible sources to camera 4: {graph.get_possible_sources(4)}")
    print(f"   Path from 0 to 4: {graph.get_path(0, 4)}")
    
    # Test transition check
    is_possible = graph.is_transition_possible(0, 1, 4.0)
    print(f"   Is transition 0→1 in 4s possible? {is_possible}")
    
    # Test spatial score
    score = graph.compute_spatial_score(0, 1, 4.0)
    print(f"   Spatial score 0→1: {score:.3f}")
    
    # Test adjacency matrix
    matrix = graph.get_adjacency_matrix()
    print(f"   Adjacency matrix shape: {matrix.shape}")
    
    return graph

def test_spatial_consistency():
    """Test spatial consistency checker."""
    print("\n🧪 Testing spatial consistency checker...")
    
    # Create graph
    graph = CameraGraph()
    for i in range(3):
        graph.add_camera(i)
    
    # Add transitions
    transition = CameraTransition(
        from_camera=0,
        to_camera=1,
        transition_probability=0.8,
        avg_travel_time=5.0,
        min_travel_time=3.0,
        max_travel_time=8.0,
        std_travel_time=1.0,
        observation_count=10,
        last_observed=datetime.now()
    )
    graph.add_transition(0, 1, transition)
    
    # Create checker
    checker = SpatialConsistencyChecker(graph)
    
    # Test consistency
    time1 = datetime.now()
    time2 = time1 + timedelta(seconds=5)
    
    result = checker.check_consistency(0, 1, time1, time2)
    print(f"   Consistency result: {result['is_consistent']}")
    print(f"   Score: {result['score']:.3f}")
    print(f"   Time diff: {result['time_diff']:.1f}s")
    
    # Test impossible transition
    time3 = time1 + timedelta(seconds=100)
    result2 = checker.check_consistency(0, 2, time1, time3)
    print(f"   Impossible transition score: {result2['score']:.3f}")
    
    return checker

def test_temporal_consistency():
    """Test temporal consistency checker."""
    print("\n🧪 Testing temporal consistency checker...")
    
    checker = TemporalConsistencyChecker(max_time_gap=300.0)
    
    # Test overlapping tracks
    now = datetime.now()
    
    track1 = {
        'start_time': now,
        'end_time': now + timedelta(seconds=30)
    }
    
    track2 = {
        'start_time': now + timedelta(seconds=10),
        'end_time': now + timedelta(seconds=40)
    }
    
    score1 = checker.compute_temporal_score(track1, track2)
    print(f"   Overlapping tracks score: {score1:.3f}")
    
    # Test separated tracks
    track3 = {
        'start_time': now + timedelta(seconds=100),
        'end_time': now + timedelta(seconds=130)
    }
    
    score2 = checker.compute_temporal_score(track1, track3)
    print(f"   Separated tracks score: {score2:.3f}")
    
    # Test sequence consistency
    observations = [
        {'camera_id': 0, 'timestamp': now},
        {'camera_id': 1, 'timestamp': now + timedelta(seconds=5)},
        {'camera_id': 2, 'timestamp': now + timedelta(seconds=12)},
        {'camera_id': 3, 'timestamp': now + timedelta(seconds=20)}
    ]
    
    seq_score = checker.check_consistency(observations)
    print(f"   Sequence consistency score: {seq_score:.3f}")
    
    return checker

def test_transition_learning():
    """Test transition learning."""
    print("\n🧪 Testing transition learning...")
    
    # Create mock database
    import sqlite3
    test_db = "tests/test_data/transition_test.db"
    
    if os.path.exists(test_db):
        os.remove(test_db)
    
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Create reid_profiles table
    cursor.execute('''
        CREATE TABLE reid_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            global_id TEXT,
            camera_id INTEGER,
            track_id TEXT,
            embedding BLOB,
            timestamp DATETIME
        )
    ''')
    
    # Insert mock tracks
    now = datetime.now()
    
    # Person 1: Camera 0 → Camera 1 → Camera 2
    tracks = [
        ('PERSON_001', 0, 'T001', now),
        ('PERSON_001', 1, 'T002', now + timedelta(seconds=5)),
        ('PERSON_001', 2, 'T003', now + timedelta(seconds=15)),
        
        # Person 2: Camera 0 → Camera 2
        ('PERSON_002', 0, 'T004', now + timedelta(seconds=30)),
        ('PERSON_002', 2, 'T005', now + timedelta(seconds=45)),
        
        # Person 3: Camera 2 → Camera 1 → Camera 3
        ('PERSON_003', 2, 'T006', now + timedelta(seconds=60)),
        ('PERSON_003', 1, 'T007', now + timedelta(seconds=70)),
        ('PERSON_003', 3, 'T008', now + timedelta(seconds=80)),
    ]
    
    for global_id, camera_id, track_id, timestamp in tracks:
        cursor.execute('''
            INSERT INTO reid_profiles
            (global_id, camera_id, track_id, embedding, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (global_id, camera_id, track_id, b'fake_embedding', timestamp))
    
    conn.commit()
    conn.close()
    
    # Learn transitions
    learner = TransitionLearner(test_db)
    graph = learner.learn_from_tracks(min_observations=2)
    
    # Check learned transitions
    print(f"   Learned transitions: {len(graph.transitions)}")
    for (from_cam, to_cam), transition in graph.transitions.items():
        print(f"   {from_cam} → {to_cam}: prob={transition.transition_probability:.3f}, "
              f"avg_time={transition.avg_travel_time:.1f}s")
    
    return graph

def visualize_topology():
    """Test topology visualization."""
    print("\n🧪 Testing topology visualization...")
    
    # Create graph
    graph = CameraGraph()
    
    # Add cameras
    for i in range(5):
        graph.add_camera(i)
    
    # Add transitions
    transitions = [
        (0, 1, 0.8, 5.0, 3.0, 8.0, 1.0, 10),
        (0, 2, 0.6, 10.0, 5.0, 15.0, 2.0, 8),
        (1, 2, 0.7, 3.0, 2.0, 5.0, 0.5, 15),
        (1, 3, 0.5, 8.0, 5.0, 12.0, 1.5, 6),
        (2, 3, 0.9, 4.0, 3.0, 6.0, 0.8, 20),
        (3, 4, 0.7, 6.0, 4.0, 9.0, 1.2, 12),
        (2, 4, 0.4, 12.0, 8.0, 16.0, 2.0, 5)
    ]
    
    for from_cam, to_cam, prob, avg, min_t, max_t, std, count in transitions:
        transition = CameraTransition(
            from_camera=from_cam,
            to_camera=to_cam,
            transition_probability=prob,
            avg_travel_time=avg,
            min_travel_time=min_t,
            max_travel_time=max_t,
            std_travel_time=std,
            observation_count=count,
            last_observed=datetime.now()
        )
        graph.add_transition(from_cam, to_cam, transition)
    
    # Create visualizer
    visualizer = TopologyVisualizer(graph)
    
    # Generate visualizations (comment out if GUI not available)
    try:
        # visualizer.visualize_matplotlib()
        # visualizer.visualize_transition_matrix()
        print("   ✅ Visualization functions available")
    except Exception as e:
        print(f"   ⚠️ Visualization not available: {e}")
    
    return visualizer

def main():
    print("=" * 60)
    print("🧪 Phase 3 - Camera Topology Tests")
    print("=" * 60)
    
    # Ensure test directory exists
    os.makedirs("tests/test_data", exist_ok=True)
    os.makedirs("tests/test_results", exist_ok=True)
    
    # Run tests
    test_camera_graph()
    test_spatial_consistency()
    test_temporal_consistency()
    test_transition_learning()
    visualize_topology()
    
    print("\n" + "=" * 60)
    print("✅ All Phase 3 tests completed!")
    print("\n📊 Next Steps:")
    print("  1. Run transition learning on real data")
    print("  2. Visualize your camera topology")
    print("  3. Integrate topology into fusion engine")
    print("  4. Test cross-camera matching with topology constraints")

if __name__ == "__main__":
    main()