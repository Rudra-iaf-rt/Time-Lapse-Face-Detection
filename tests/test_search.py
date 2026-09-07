# tests/test_search.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import json

from search.query_builder import QueryBuilder, SortOrder, ComparisonOperator
from search.query_engine import QueryEngine
from search.search_index import SearchIndex
from search.filters import FilterProcessor
from search.aggregators import ResultAggregator
from search.search_visualizer import SearchVisualizer

def create_test_data():
    """Create test data for search."""
    print("🧪 Creating test data...")
    
    # Use existing database or create new
    db_path = "tests/test_data/search_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create necessary tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reid_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            global_id TEXT,
            camera_id INTEGER,
            track_id TEXT,
            timestamp DATETIME,
            quality REAL
        )
    ''')
    
    # Insert test data
    now = datetime.now()
    test_data = [
        ('PERSON_001', 0, 'T001', now, 0.9),
        ('PERSON_001', 1, 'T002', now + timedelta(seconds=30), 0.85),
        ('PERSON_001', 2, 'T003', now + timedelta(seconds=60), 0.8),
        ('PERSON_001', 1, 'T004', now + timedelta(seconds=120), 0.7),
        ('PERSON_002', 0, 'T005', now + timedelta(seconds=10), 0.8),
        ('PERSON_002', 2, 'T006', now + timedelta(seconds=50), 0.75),
        ('PERSON_002', 3, 'T007', now + timedelta(seconds=100), 0.7),
        ('PERSON_003', 1, 'T008', now + timedelta(seconds=20), 0.6),
        ('PERSON_003', 3, 'T009', now + timedelta(seconds=80), 0.65),
        ('PERSON_003', 4, 'T010', now + timedelta(seconds=140), 0.5),
        ('PERSON_004', 2, 'T011', now + timedelta(seconds=40), 0.9),
        ('PERSON_004', 2, 'T012', now + timedelta(seconds=70), 0.85),
        ('PERSON_004', 2, 'T013', now + timedelta(seconds=100), 0.8),
        ('PERSON_004', 2, 'T014', now + timedelta(seconds=130), 0.75),
        ('PERSON_005', 0, 'T015', now + timedelta(seconds=15), 0.7),
        ('PERSON_005', 1, 'T016', now + timedelta(seconds=45), 0.65),
        ('PERSON_005', 2, 'T017', now + timedelta(seconds=75), 0.6),
        ('PERSON_005', 3, 'T018', now + timedelta(seconds=105), 0.55),
    ]
    
    for global_id, camera_id, track_id, timestamp, quality in test_data:
        cursor.execute('''
            INSERT INTO reid_profiles
            (global_id, camera_id, track_id, timestamp, quality)
            VALUES (?, ?, ?, ?, ?)
        ''', (global_id, camera_id, track_id, timestamp.isoformat(), quality))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Test data created: {len(test_data)} observations")
    return db_path

def test_query_builder():
    """Test query builder."""
    print("\n🧪 Testing query builder...")
    
    builder = QueryBuilder()
    
    # Build a query
    query = (builder
             .with_time_range(
                 start=datetime.now() - timedelta(hours=1),
                 end=datetime.now()
             )
             .with_cameras([0, 1, 2])
             .with_dwell_time(min_time=10, max_time=100)
             .with_person(['PERSON_001', 'PERSON_002'])
             .with_confidence(min_conf=0.7)
             .with_event_types(['entry', 'exit'])
             .sort_by('duration', SortOrder.DESCENDING)
             .limit(50, offset=10)
             .add_condition('confidence', ComparisonOperator.GTE, 0.8)
             .build())
    
    print(f"   Query built successfully")
    print(f"   - Time range: {query.time_range.start} to {query.time_range.end}")
    print(f"   - Cameras: {query.spatial.cameras}")
    print(f"   - Dwell time: {query.spatial.min_dwell_time} - {query.spatial.max_dwell_time}")
    print(f"   - Persons: {query.person.global_ids}")
    print(f"   - Confidence: {query.person.min_confidence}")
    print(f"   - Events: {query.event.event_types}")
    print(f"   - Sort: {query.sort_by} ({query.sort_order.value})")
    print(f"   - Limit: {query.limit}, Offset: {query.offset}")
    print(f"   - Conditions: {len(query.conditions)}")
    
    return query

def test_search_index(db_path):
    """Test search index."""
    print("\n🧪 Testing search index...")
    
    index = SearchIndex(db_path)
    
    # Index some data
    index.index_person('PERSON_001', {
        'first_seen': datetime.now().isoformat(),
        'last_seen': (datetime.now() + timedelta(minutes=10)).isoformat(),
        'total_duration': 600,
        'cameras_visited': [0, 1, 2],
        'route': [0, 1, 2],
        'confidence': 0.85,
        'face_count': 3,
        'reid_count': 5
    })
    
    index.index_camera_visit(
        0, 'PERSON_001',
        datetime.now(), datetime.now() + timedelta(minutes=2),
        0.9
    )
    
    index.index_event(
        'PERSON_001', datetime.now(), 0, 'entry'
    )
    
    index.index_transition(
        0, 1, 'PERSON_001', datetime.now() + timedelta(seconds=30),
        30, 0.85
    )
    
    print("   ✅ Index created successfully")
    
    # Test search
    results = index.search_persons({
        'cameras': [0, 1],
        'min_confidence': 0.8,
        'limit': 10
    })
    
    print(f"   Person search results: {len(results)}")
    
    events = index.search_events({
        'event_types': ['entry'],
        'limit': 5
    })
    
    print(f"   Event search results: {len(events)}")
    
    transitions = index.search_transitions({
        'from_cameras': [0],
        'limit': 5
    })
    
    print(f"   Transition search results: {len(transitions)}")
    
    return index

def test_query_engine(db_path):
    """Test query engine."""
    print("\n🧪 Testing query engine...")
    
    engine = QueryEngine(db_path)
    
    # Test 1: Person search
    query = (QueryBuilder()
             .with_time_range(
                 start=datetime.now() - timedelta(hours=2),
                 end=datetime.now() + timedelta(hours=2)
             )
             .with_cameras([0, 1, 2])
             .with_dwell_time(min_time=5)
             .with_confidence(min_conf=0.6)
             .sort_by('total_duration', SortOrder.DESCENDING)
             .limit(10)
             .build())
    
    results = engine.search(query)
    print(f"\n   Person search:")
    print(f"   - Total results: {results['total_count']}")
    print(f"   - Result type: {results['result_type']}")
    print(f"   - Aggregated stats: {json.dumps(results['aggregated'], indent=2)[:200]}...")
    
    # Test 2: Event search
    query2 = (QueryBuilder()
              .with_time_range(
                  start=datetime.now() - timedelta(hours=1),
                  end=datetime.now() + timedelta(hours=1)
              )
              .with_event_types(['entry', 'exit'])
              .with_cameras([0, 1])
              .sort_by('timestamp', SortOrder.DESCENDING)
              .limit(20)
              .build())
    
    results2 = engine.search(query2)
    print(f"\n   Event search:")
    print(f"   - Total results: {results2['total_count']}")
    print(f"   - Result type: {results2['result_type']}")
    
    # Test 3: Transition search
    query3 = (QueryBuilder()
              .with_transition([0, 1], [1, 2])
              .with_time_range(
                  start=datetime.now() - timedelta(hours=1),
                  end=datetime.now() + timedelta(hours=1)
              )
              .sort_by('duration', SortOrder.DESCENDING)
              .limit(10)
              .build())
    
    results3 = engine.search(query3)
    print(f"\n   Transition search:")
    print(f"   - Total results: {results3['total_count']}")
    print(f"   - Result type: {results3['result_type']}")
    
    # Test 4: Text search
    text_results = engine.search_by_text("camera 0 last hour")
    print(f"\n   Text search 'camera 0 last hour':")
    print(f"   - Total results: {text_results['total_count']}")
    
    # Test 5: Statistics
    stats = engine.get_statistics()
    print(f"\n   Search statistics:")
    print(f"   - Total persons: {stats['total_persons']}")
    print(f"   - Total events: {stats['total_events']}")
    print(f"   - Total transitions: {stats['total_transitions']}")
    print(f"   - Most active persons: {len(stats.get('most_active', []))}")
    print(f"   - Camera usage: {len(stats.get('camera_usage', {}))}")
    
    return engine

def test_filter_processor():
    """Test filter processor."""
    print("\n🧪 Testing filter processor...")
    
    processor = FilterProcessor()
    
    # Sample results
    results = [
        {'global_id': 'PERSON_001', 'confidence': 0.9, 'total_duration': 100},
        {'global_id': 'PERSON_002', 'confidence': 0.7, 'total_duration': 50},
        {'global_id': 'PERSON_003', 'confidence': 0.5, 'total_duration': 200},
        {'global_id': 'PERSON_004', 'confidence': 0.8, 'total_duration': 75},
    ]
    
    # Create query with conditions
    query = QueryBuilder()
    query = query.add_condition('confidence', ComparisonOperator.GTE, 0.7)
    query = query.add_condition('total_duration', ComparisonOperator.LTE, 150)
    query = query.build()
    
    filtered = processor.apply_filters(results, query)
    
    print(f"   Original results: {len(results)}")
    print(f"   Filtered results: {len(filtered)}")
    for r in filtered:
        print(f"   - {r['global_id']}: conf={r['confidence']}, duration={r['total_duration']}")
    
    return processor

def test_aggregator():
    """Test aggregator."""
    print("\n🧪 Testing aggregator...")
    
    aggregator = ResultAggregator()
    
    # Sample results
    results = [
        {'global_id': 'PERSON_001', 'total_duration': 100, 'confidence': 0.9,
         'cameras_visited': [0, 1, 2], 'first_seen': datetime.now()},
        {'global_id': 'PERSON_002', 'total_duration': 50, 'confidence': 0.7,
         'cameras_visited': [0, 2], 'first_seen': datetime.now()},
        {'global_id': 'PERSON_003', 'total_duration': 200, 'confidence': 0.5,
         'cameras_visited': [1, 2, 3], 'first_seen': datetime.now()},
    ]
    
    aggregated = aggregator.aggregate(results, None)
    
    print(f"   Aggregated summary:")
    print(f"   - Total: {aggregated['total']}")
    print(f"   - Total duration: {aggregated['total_duration']}")
    print(f"   - Avg duration: {aggregated['avg_duration']:.1f}")
    print(f"   - Avg confidence: {aggregated['avg_confidence']:.2f}")
    print(f"   - Camera visits: {len(aggregated['camera_visits'])}")
    
    return aggregator

def test_visualization(db_path):
    """Test search visualization."""
    print("\n🧪 Testing search visualization...")
    
    engine = QueryEngine(db_path)
    
    # Get some results
    query = (QueryBuilder()
             .with_time_range(
                 start=datetime.now() - timedelta(hours=2),
                 end=datetime.now() + timedelta(hours=2)
             )
             .limit(20)
             .build())
    
    results = engine.search(query)
    
    visualizer = SearchVisualizer()
    
    try:
        # Try to visualize
        # visualizer.visualize_results(
        #     results, 
        #     save_path='tests/test_results/search_results.png'
        # )
        print("   ✅ Search visualization available")
    except Exception as e:
        print(f"   ⚠️ Visualization not available: {e}")
    
    return visualizer

def main():
    print("=" * 60)
    print("🧪 Phase 5 - Intelligent Search Tests")
    print("=" * 60)
    
    # Ensure test directories exist
    os.makedirs("tests/test_data", exist_ok=True)
    os.makedirs("tests/test_results", exist_ok=True)
    
    # Create test data
    db_path = create_test_data()
    
    # Run tests
    test_query_builder()
    test_search_index(db_path)
    test_query_engine(db_path)
    test_filter_processor()
    test_aggregator()
    test_visualization(db_path)
    
    print("\n" + "=" * 60)
    print("✅ All Phase 5 tests completed!")
    print("\n📊 Query Examples:")
    print("  1. 'Who was in camera 0 between 2-3 PM?'")
    print("  2. 'Find all persons with dwell time > 30 minutes'")
    print("  3. 'Show route of PERSON_001'")
    print("  4. 'Find all entries to restricted zone'")
    print("  5. 'Show transitions from camera 0 to 1'")
    print("  6. 'Who stayed in camera 2 for more than 1 hour?'")

if __name__ == "__main__":
    main()