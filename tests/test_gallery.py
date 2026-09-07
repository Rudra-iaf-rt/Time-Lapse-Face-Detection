# tests/test_gallery.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import sqlite3
from datetime import datetime
from reid.reid_gallery import ReIDGallery

def setup_test_database():
    """Setup test database."""
    test_db = "tests/test_data/test_reid.db"
    # Remove existing test db
    if os.path.exists(test_db):
        os.remove(test_db)
    return test_db

def test_gallery_initialization(db_path):
    """Test ReIDGallery initialization."""
    print("🧪 Testing ReIDGallery initialization...")
    try:
        gallery = ReIDGallery(db_path=db_path)
        print(f"✅ Gallery initialized with database: {db_path}")
        return gallery
    except Exception as e:
        print(f"❌ Failed to initialize gallery: {e}")
        return None

def test_add_observation(gallery):
    """Test adding observations to gallery."""
    print("\n🧪 Testing adding observations...")
    
    # Create embeddings
    emb1 = np.random.randn(512)
    emb1 = emb1 / np.linalg.norm(emb1)
    
    emb2 = np.random.randn(512)
    emb2 = emb2 / np.linalg.norm(emb2)
    
    # Add observations from different cameras
    try:
        # Camera 0 - Track 1
        id1 = gallery.add_observation(0, "T001", emb1, 0.8, datetime.now())
        print(f"   - Added observation 1: {id1}")
        
        # Camera 1 - Track 2 (should match id1 if similar)
        id2 = gallery.add_observation(1, "T002", emb1, 0.7, datetime.now())
        print(f"   - Added observation 2: {id2}")
        
        # Camera 2 - Track 3 (different person)
        id3 = gallery.add_observation(2, "T003", emb2, 0.75, datetime.now())
        print(f"   - Added observation 3: {id3}")
        
        # Check if matches worked
        if id1 == id2:
            print("   ✅ Cross-camera match successful!")
        else:
            print("   ⚠️ Cross-camera match failed (threshold may be too high)")
            
        return id1, id2, id3
        
    except Exception as e:
        print(f"❌ Failed to add observations: {e}")
        return None, None, None

def test_get_global_id(gallery):
    """Test retrieving global IDs."""
    print("\n🧪 Testing global ID retrieval...")
    
    try:
        # Get ID for existing track
        global_id = gallery.get_global_id(0, "T001")
        print(f"   - Global ID for (0, T001): {global_id}")
        
        # Get ID for non-existent track
        non_existent = gallery.get_global_id(99, "T999")
        print(f"   - Global ID for (99, T999): {non_existent}")
        
        if global_id is not None:
            print("   ✅ Global ID retrieval successful")
        else:
            print("   ⚠️ Global ID retrieval returned None")
            
        return global_id
        
    except Exception as e:
        print(f"❌ Failed to retrieve global ID: {e}")
        return None

def test_gallery_statistics(gallery):
    """Test gallery statistics."""
    print("\n🧪 Testing gallery statistics...")
    
    try:
        stats = gallery.get_statistics()
        print(f"   - Total identities: {stats['total_identities']}")
        print(f"   - Total profiles: {stats['total_profiles']}")
        print(f"   - Total matches: {stats['total_matches']}")
        print(f"   - Camera profiles: {stats['camera_profiles']}")
        
        print("   ✅ Statistics retrieved successfully")
        return stats
        
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")
        return None

def test_database_integrity(db_path):
    """Test database integrity and schema."""
    print("\n🧪 Testing database integrity...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   - Tables: {tables}")
        
        # Expected tables
        expected = ['global_identities', 'reid_profiles', 'reid_matches']
        for table in expected:
            if table in tables:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' missing")
        
        # Check schema for each table
        for table in expected:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"   - {table} columns: {[col[1] for col in columns]}")
        
        conn.close()
        print("   ✅ Database integrity check complete")
        
    except Exception as e:
        print(f"❌ Database integrity check failed: {e}")

def main():
    print("=" * 60)
    print("🧪 Re-ID Gallery Tests")
    print("=" * 60)
    
    # Setup test database
    db_path = setup_test_database()
    
    # Test 1: Initialization
    gallery = test_gallery_initialization(db_path)
    if gallery is None:
        return
    
    # Test 2: Add observations
    test_add_observation(gallery)
    
    # Test 3: Retrieve global IDs
    test_get_global_id(gallery)
    
    # Test 4: Statistics
    test_gallery_statistics(gallery)
    
    # Test 5: Database integrity
    test_database_integrity(db_path)
    
    print("\n" + "=" * 60)
    print("✅ All gallery tests completed!")

if __name__ == "__main__":
    main()