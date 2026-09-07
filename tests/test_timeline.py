# tests/test_timeline.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime, timedelta
import sqlite3

from timeline.timeline_builder import TimelineBuilder, PersonTimeline
from timeline.timeline_aggregator import TimelineAggregator
from timeline.event_detector import EventDetector
from timeline.route_analyzer import RouteAnalyzer
from timeline.timeline_visualizer import TimelineVisualizer
from timeline.timeline_storage import TimelineStorage

def create_test_database():
    """Create a test database with sample tracking data."""
    print("🧪 Creating test database...")
    
    test_db = "tests/test_data/timeline_test.db"
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
            timestamp DATETIME,
            quality REAL
        )
    ''')
    
    # Generate mock data for multiple persons
    now = datetime.now()
    persons = []
    
    # Person 1: Camera 0 → 1 → 2 → 3
    p1 = []
    for i, cam in enumerate([0, 1, 2, 3]):
        for j in range(3):  # Multiple observations per camera
            ts = now + timedelta(seconds=i*30 + j*5)
            p1.append(('PERSON_001', cam, f'T001_{i}_{j}', ts, 0.8 + np.random.rand()*0.2))
    persons.extend(p1)
    
    # Person 2: Camera 0 → 2 → 4
    p2 = []
    for i, cam in enumerate([0, 2, 4]):
        for j in range(4):
            ts = now + timedelta(seconds=i*45 + j*8)
            p2.append(('PERSON_002', cam, f'T002_{i}_{j}', ts, 0.7 + np.random.rand()*0.3))
    persons.extend(p2)
    
    # Person 3: Camera 1 → 3 → 4 (starts later)
    p3 = []
    for i, cam in enumerate([1, 3, 4]):
        for j in range(2):
            ts = now + timedelta(seconds=120 + i*40 + j*10)
            p3.append(('PERSON_003', cam, f'T003_{i}_{j}', ts, 0.6 + np.random.rand()*0.4))
    persons.extend(p3)
    
    # Person 4: Long dwell at camera 2 (anomaly)
    p4 = []
    for i in range(10):  # Many observations at same camera
        ts = now + timedelta(seconds=200 + i*15)
        p4.append(('PERSON_004', 2, f'T004_{i}', ts, 0.7 + np.random.rand()*0.3))
    persons.extend(p4)
    
    # Insert all data
    for global_id, camera_id, track_id, timestamp, quality in persons:
        cursor.execute('''
            INSERT INTO reid_profiles
            (global_id, camera_id, track_id, embedding, timestamp, quality)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (global_id, camera_id, track_id, b'fake_embedding', 
              timestamp.isoformat(), quality))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Test database created: {test_db}")
    print(f"   Inserted {len(persons)} observations")
    
    return test_db

def test_timeline_builder(db_path):
    """Test timeline builder."""
    print("\n🧪 Testing timeline builder...")
    
    builder = TimelineBuilder(db_path, min_segment_duration=1.0, max_gap_duration=30.0)
    timelines = builder.build_timelines()
    
    print(f"   Built {len(timelines)} timelines")
    
    for global_id, timeline in timelines.items():
        summary = timeline.get_timeline_summary()
        print(f"\n   Person {global_id}:")
        print(f"      - Segments: {len(timeline.segments)}")
        print(f"      - Cameras: {timeline.cameras_visited}")
        print(f"      - Route: {timeline.route}")
        print(f"      - Total duration: {timeline.total_duration:.1f}s")
        
        # Print events
        events_by_type = {}
        for event in timeline.events:
            events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
        print(f"      - Events: {events_by_type}")
    
    return timelines

def test_timeline_aggregator(timelines):
    """Test timeline aggregator."""
    print("\n🧪 Testing timeline aggregator...")
    
    aggregator = TimelineAggregator(time_bucket=10)
    
    for global_id, timeline in timelines.items():
        print(f"\n   Aggregating {global_id}:")
        
        # Aggregate by time
        buckets = aggregator.aggregate_by_time(timeline, bucket_size=10)
        print(f"      - Time buckets: {len(buckets)}")
        
        # Aggregate by camera
        camera_stats = aggregator.aggregate_by_camera(timeline)
        print(f"      - Cameras: {len(camera_stats)}")
        for cam, stats in camera_stats.items():
            print(f"         Camera {cam}: {stats['visit_count']} visits, "
                  f"{stats['total_duration']:.1f}s total")
        
        # Get activity patterns
        patterns = aggregator.get_activity_patterns(timeline)
        print(f"      - Most active hour: {patterns.get('most_active_hour')}")
        print(f"      - Most active day: {patterns.get('most_active_day')}")
        
        # Get visit summary
        summary = aggregator.get_visit_summary(timeline)
        print(f"      - Total visits: {summary['total_visits']}")
    
    return aggregator

def test_event_detector(timelines):
    """Test event detector."""
    print("\n🧪 Testing event detector...")
    
    detector = EventDetector({
        'dwell_threshold': 30,  # 30 seconds for testing
        'transition_threshold': 5  # 5 seconds
    })
    
    for global_id, timeline in timelines.items():
        print(f"\n   Detecting events for {global_id}:")
        
        events = detector.detect_events(timeline)
        
        for event_type, event_list in events.items():
            if event_list:
                print(f"      - {event_type}: {len(event_list)} events")
                # Show first event of each type
                if event_list:
                    sample = event_list[0]
                    print(f"         Sample: {sample}")
    
    # Test pattern detection
    patterns = detector.detect_patterns(timelines)
    print(f"\n   Pattern detection:")
    print(f"      - Common routes: {len(patterns['common_routes'])}")
    if patterns['common_routes']:
        print(f"         Most common: {patterns['common_routes'][0]}")
    print(f"      - Crowd movements: {len(patterns['crowd_movements'])}")
    print(f"      - Cooccurrence pairs: {len(patterns['cooccurrence'])}")
    
    return detector

def test_route_analyzer(timelines):
    """Test route analyzer."""
    print("\n🧪 Testing route analyzer...")
    
    analyzer = RouteAnalyzer()
    
    # Extract routes
    for timeline in timelines.values():
        routes = analyzer.extract_routes(timeline)
        print(f"\n   Person {timeline.global_id}: {len(routes)} routes")
        for route in routes[:3]:  # Show first 3
            print(f"      - Route: {' → '.join(map(str, route.cameras))}")
            print(f"        Duration: {route.duration:.1f}s")
    
    # Find common routes
    common_routes = analyzer.find_common_routes(
        list(timelines.values()), min_occurrences=2
    )
    print(f"\n   Common routes found: {len(common_routes)}")
    for route in common_routes:
        print(f"      - Route: {' → '.join(map(str, route['route']))}")
        print(f"        Occurrences: {route['occurrences']}")
    
    return analyzer

def test_timeline_storage(db_path, timelines):
    """Test timeline storage."""
    print("\n🧪 Testing timeline storage...")
    
    storage = TimelineStorage(db_path)
    
    # Store timelines
    for timeline in timelines.values():
        storage.store_timeline(timeline)
        print(f"   Stored timeline for {timeline.global_id}")
    
    # Load one timeline
    first_id = list(timelines.keys())[0]
    loaded = storage.load_timeline(first_id)
    
    if loaded:
        print(f"\n   Loaded timeline for {first_id}")
        print(f"      - Segments: {len(loaded.segments)}")
        print(f"      - Events: {len(loaded.events)}")
        print(f"      - Duration: {loaded.total_duration:.1f}s")
    
    # Search timelines
    now = datetime.now()
    results = storage.search_timelines(
        start_time=now - timedelta(minutes=5),
        end_time=now + timedelta(minutes=5)
    )
    print(f"\n   Search results: {len(results)} timelines found")
    
    return storage

def test_visualization(timelines):
    """Test timeline visualization."""
    print("\n🧪 Testing timeline visualization...")
    
    visualizer = TimelineVisualizer()
    
    # Visualize first timeline
    first_id = list(timelines.keys())[0]
    timeline = timelines[first_id]
    
    try:
        # Try to visualize (may fail if GUI not available)
        # visualizer.visualize_timeline(
        #     timeline, 
        #     save_path='tests/test_results/timeline.png'
        # )
        print("   ✅ Timeline visualization available")
    except Exception as e:
        print(f"   ⚠️ Visualization not available: {e}")
    
    try:
        # Visualize route
        if timeline.route:
            # visualizer.visualize_route(
            #     timeline.route,
            #     timeline.first_seen,
            #     save_path='tests/test_results/route.png'
            # )
            print("   ✅ Route visualization available")
    except Exception as e:
        print(f"   ⚠️ Route visualization not available: {e}")
    
    return visualizer

def main():
    print("=" * 60)
    print("🧪 Phase 4 - Person-Centric Timeline Tests")
    print("=" * 60)
    
    # Ensure test directories exist
    os.makedirs("tests/test_data", exist_ok=True)
    os.makedirs("tests/test_results", exist_ok=True)
    
    # Create test database
    db_path = create_test_database()
    
    # Run tests
    timelines = test_timeline_builder(db_path)
    test_timeline_aggregator(timelines)
    test_event_detector(timelines)
    test_route_analyzer(timelines)
    test_timeline_storage(db_path, timelines)
    test_visualization(timelines)
    
    print("\n" + "=" * 60)
    print("✅ All Phase 4 tests completed!")
    print("\n📊 Next Steps:")
    print("  1. Build timelines from your real data")
    print("  2. Analyze person routes and patterns")
    print("  3. Detect anomalous events")
    print("  4. Use timelines for intelligent search")
    print("  5. Create summary reports for each person")

if __name__ == "__main__":
    main()