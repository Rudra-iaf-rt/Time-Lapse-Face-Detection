# tests/test_database.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import numpy as np
from datetime import datetime, timedelta
import json

from database.postgres_manager import PostgresManager
from database.qdrant_manager import QdrantManager
from database.redis_manager import RedisManager

async def test_postgres():
    """Test PostgreSQL operations."""
    print("\n🧪 Testing PostgreSQL...")
    
    config = {
        'postgres': {
            'host': 'localhost',
            'port': 5432,
            'database': 'multicam_reid',
            'user': 'postgres',
            'password': 'postgres'
        }
    }
    
    manager = PostgresManager(config)
    await manager.initialize()
    
    # Create a person
    person_data = {
        'global_id': 'TEST_001',
        'first_seen': datetime.now(),
        'last_seen': datetime.now(),
        'confidence': 0.9,
        'metadata': {'test': True}
    }
    
    person = await manager.create_person(person_data)
    print(f"   Created person: {person['global_id']}")
    
    # Get person
    retrieved = await manager.get_person('TEST_001')
    print(f"   Retrieved person: {retrieved['global_id']}")
    
    # Create camera
    camera_data = {
        'camera_id': 0,
        'name': 'Test Camera',
        'location': 'Test Lab',
        'capacity': 50
    }
    camera = await manager.create_camera(camera_data)
    print(f"   Created camera: {camera['camera_id']}")
    
    # Create observation
    observation_data = {
        'track_id': 'TEST_TRACK_001',
        'global_id': 'TEST_001',
        'camera_id': 0,
        'bbox': [10, 20, 30, 40],
        'confidence': 0.95,
        'quality': 0.8
    }
    observation = await manager.create_observation(observation_data)
    print(f"   Created observation: {observation['id']}")
    
    # Get observations
    observations = await manager.get_observations('TEST_001')
    print(f"   Retrieved {len(observations)} observations")
    
    # Get camera statistics
    stats = await manager.get_camera_statistics(
        0,
        datetime.now() - timedelta(hours=1),
        datetime.now()
    )
    print(f"   Camera statistics: {stats['observation_count']} observations")
    
    # Cleanup
    await manager.close()
    print("   ✅ PostgreSQL tests passed")
    
    return manager

async def test_qdrant():
    """Test Qdrant operations."""
    print("\n🧪 Testing Qdrant...")
    
    config = {
        'qdrant': {
            'host': 'localhost',
            'port': 6333,
            'vector_size': 512,
            'distance': 'Cosine',
            'face_collection': 'test_face_embeddings',
            'reid_collection': 'test_reid_embeddings',
            'appearance_collection': 'test_appearance_embeddings'
        }
    }
    
    manager = QdrantManager(config)
    manager.initialize()
    
    # Create embeddings
    face_emb = np.random.randn(512)
    face_emb = face_emb / np.linalg.norm(face_emb)
    
    reid_emb = np.random.randn(512)
    reid_emb = reid_emb / np.linalg.norm(reid_emb)
    
    # Upsert embeddings
    success = manager.upsert_face_embedding(
        'TEST_001',
        face_emb,
        {'camera_id': 0, 'timestamp': datetime.now().isoformat()}
    )
    print(f"   Upserted face embedding: {success}")
    
    success = manager.upsert_reid_embedding(
        'TEST_001',
        reid_emb,
        {'camera_id': 0, 'timestamp': datetime.now().isoformat()}
    )
    print(f"   Upserted Re-ID embedding: {success}")
    
    # Search embeddings
    results = manager.search_face_embeddings(face_emb, limit=5)
    print(f"   Found {len(results)} face matches")
    
    if results:
        print(f"   Best match score: {results[0]['score']:.3f}")
    
    # Get collection stats
    stats = manager.get_collection_stats('test_face_embeddings')
    print(f"   Collection stats: {stats['vectors_count']} vectors")
    
    # Cleanup
    manager.delete_embeddings_for_person('TEST_001')
    print("   ✅ Qdrant tests passed")
    
    return manager

async def test_redis():
    """Test Redis operations."""
    print("\n🧪 Testing Redis...")
    
    config = {
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'key_prefix': 'test_multicam'
        }
    }
    
    manager = RedisManager(config)
    await manager.initialize()
    
    # Test track operations
    track_data = {
        'track_id': 'TEST_TRACK_001',
        'global_id': 'TEST_001',
        'camera_id': 0,
        'bbox': [10, 20, 30, 40]
    }
    
    await manager.set_track('TEST_TRACK_001', track_data)
    print("   Stored track")
    
    track = await manager.get_track('TEST_TRACK_001')
    print(f"   Retrieved track: {track['track_id']}")
    
    # Test camera state
    camera_state = {
        'occupancy': 5,
        'active_tracks': ['TEST_TRACK_001']
    }
    await manager.set_camera_state(0, camera_state)
    print("   Stored camera state")
    
    state = await manager.get_camera_state(0)
    print(f"   Retrieved camera state: {state['occupancy']} people")
    
    # Test caching
    await manager.cache_set('test_key', {'data': 'test_value'}, ttl=60)
    cached = await manager.cache_get('test_key')
    print(f"   Retrieved cache: {cached}")
    
    # Test publishing
    await manager.publish_event('test_channel', {'event': 'test'})
    print("   Published event")
    
    # Get stats
    stats = await manager.get_cache_stats()
    print(f"   Cache stats: {stats['total_keys']} keys")
    
    # Cleanup
    await manager.close()
    print("   ✅ Redis tests passed")
    
    return manager

async def test_integration():
    """Test integration of all databases."""
    print("\n🧪 Testing database integration...")
    
    # Create managers
    postgres_config = {
        'postgres': {
            'host': 'localhost',
            'port': 5432,
            'database': 'multicam_reid',
            'user': 'postgres',
            'password': 'postgres'
        }
    }
    
    qdrant_config = {
        'qdrant': {
            'host': 'localhost',
            'port': 6333,
            'vector_size': 512,
            'distance': 'Cosine',
            'face_collection': 'test_face_embeddings',
            'reid_collection': 'test_reid_embeddings',
            'appearance_collection': 'test_appearance_embeddings'
        }
    }
    
    redis_config = {
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'key_prefix': 'test_multicam'
        }
    }
    
    # Initialize all
    postgres = PostgresManager(postgres_config)
    await postgres.initialize()
    
    qdrant = QdrantManager(qdrant_config)
    qdrant.initialize()
    
    redis = RedisManager(redis_config)
    await redis.initialize()
    
    # Create a person with all data
    person_data = {
        'global_id': 'INTEGRATION_001',
        'first_seen': datetime.now(),
        'last_seen': datetime.now(),
        'confidence': 0.95
    }
    
    # PostgreSQL
    person = await postgres.create_person(person_data)
    print(f"   Created person in PostgreSQL: {person['global_id']}")
    
    # Qdrant
    embedding = np.random.randn(512)
    embedding = embedding / np.linalg.norm(embedding)
    qdrant.upsert_face_embedding(
        'INTEGRATION_001',
        embedding,
        {'camera_id': 0}
    )
    print("   Stored embedding in Qdrant")
    
    # Redis
    await redis.cache_person('INTEGRATION_001', person_data)
    cached = await redis.get_cached_person('INTEGRATION_001')
    print(f"   Cached person in Redis: {cached['global_id']}")
    
    # Search across databases
    results = qdrant.search_face_embeddings(embedding, limit=5)
    print(f"   Found {len(results)} matches in Qdrant")
    
    # Cleanup
    await postgres.close()
    await redis.close()
    
    print("   ✅ Integration tests passed")

async def main():
    print("=" * 60)
    print("🧪 Phase 8 - Database Integration Tests")
    print("=" * 60)
    
    try:
        await test_postgres()
        await test_qdrant()
        await test_redis()
        await test_integration()
        
        print("\n" + "=" * 60)
        print("✅ All Phase 8 tests completed!")
        print("\n📊 Database Features:")
        print("  1. PostgreSQL for relational data")
        print("  2. Qdrant for vector embeddings")
        print("  3. Redis for caching and real-time data")
        print("  4. Async operations support")
        print("  5. Connection pooling")
        print("  6. Data migration support")
        print("  7. Docker containerization")
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())