# database/redis_manager.py
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    """
    Redis cache manager for live data.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.redis_config = config.get('redis', {})
        
        # Connection parameters
        self.host = self.redis_config.get('host', 'localhost')
        self.port = self.redis_config.get('port', 6379)
        self.db = self.redis_config.get('db', 0)
        self.password = self.redis_config.get('password', None)
        self.pool_size = self.redis_config.get('pool_size', 10)
        
        # Prefixes for keys
        self.key_prefix = self.redis_config.get('key_prefix', 'multicam')
        
        # TTLs (in seconds)
        self.ttl = {
            'track': self.redis_config.get('track_ttl', 300),  # 5 minutes
            'camera_state': self.redis_config.get('camera_ttl', 60),  # 1 minute
            'person': self.redis_config.get('person_ttl', 3600),  # 1 hour
            'websocket': self.redis_config.get('websocket_ttl', 60),  # 1 minute
            'cache': self.redis_config.get('cache_ttl', 300)  # 5 minutes
        }
        
        # Initialize client
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
        
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                max_connections=self.pool_size
            )
            
            # Test connection
            await self.client.ping()
            
            self._initialized = True
            logger.info(f"OK: Redis connected to {self.host}:{self.port}/{self.db}")
            
        except Exception as e:
            logger.error(f"ERROR: Failed to connect to Redis: {e}")
            raise
    
    def _get_key(self, *parts) -> str:
        """Generate a Redis key with prefix."""
        return f"{self.key_prefix}:{':'.join(str(p) for p in parts)}"
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            close_fn = getattr(self.client, "aclose", None) or self.client.close
            result = close_fn()
            if hasattr(result, "__await__"):
                await result
            logger.info("OK: Redis connection closed")
    
    # Track Operations
    async def set_track(self, track_id: str, track_data: Dict):
        """Store track data."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('track', track_id)
        await self.client.setex(
            key,
            self.ttl['track'],
            json.dumps(track_data)
        )
    
    async def get_track(self, track_id: str) -> Optional[Dict]:
        """Get track data."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('track', track_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def delete_track(self, track_id: str):
        """Delete track data."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('track', track_id)
        await self.client.delete(key)
    
    async def get_all_tracks(self) -> List[Dict]:
        """Get all active tracks."""
        if not self._initialized:
            await self.initialize()
        
        pattern = self._get_key('track', '*')
        keys = await self.client.keys(pattern)
        
        tracks = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                tracks.append(json.loads(data))
        
        return tracks
    
    # Camera State Operations
    async def set_camera_state(self, camera_id: int, state: Dict):
        """Store camera state."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('camera', camera_id)
        state['timestamp'] = datetime.now().isoformat()
        await self.client.setex(
            key,
            self.ttl['camera_state'],
            json.dumps(state)
        )
    
    async def get_camera_state(self, camera_id: int) -> Optional[Dict]:
        """Get camera state."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('camera', camera_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def get_all_camera_states(self) -> Dict[int, Dict]:
        """Get all camera states."""
        if not self._initialized:
            await self.initialize()
        
        pattern = self._get_key('camera', '*')
        keys = await self.client.keys(pattern)
        
        states = {}
        for key in keys:
            camera_id = int(key.split(':')[-1])
            data = await self.client.get(key)
            if data:
                states[camera_id] = json.loads(data)
        
        return states
    
    # Person Cache Operations
    async def cache_person(self, global_id: str, person_data: Dict):
        """Cache person data."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('person', global_id)
        await self.client.setex(
            key,
            self.ttl['person'],
            json.dumps(person_data)
        )
    
    async def get_cached_person(self, global_id: str) -> Optional[Dict]:
        """Get cached person data."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('person', global_id)
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    # WebSocket Event Operations
    async def publish_event(self, channel: str, event: Dict):
        """Publish a WebSocket event."""
        if not self._initialized:
            await self.initialize()
        
        event['timestamp'] = datetime.now().isoformat()
        await self.client.publish(
            channel,
            json.dumps(event)
        )
    
    async def subscribe_events(self, channel: str):
        """Subscribe to WebSocket events."""
        if not self._initialized:
            await self.initialize()
        
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    async def get_recent_events(self, channel: str, limit: int = 10) -> List[Dict]:
        """Get recent events from a channel."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('events', channel)
        events = await self.client.lrange(key, 0, limit - 1)
        
        return [json.loads(e) for e in events if e]
    
    async def push_event(self, channel: str, event: Dict):
        """Push an event to a channel's history."""
        if not self._initialized:
            await self.initialize()
        
        key = self._get_key('events', channel)
        event['timestamp'] = datetime.now().isoformat()
        await self.client.lpush(key, json.dumps(event))
        await self.client.ltrim(key, 0, 99)  # Keep last 100 events
        await self.client.expire(key, self.ttl['websocket'])
    
    # General Cache Operations
    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a cache value."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._get_key('cache', key)
        await self.client.setex(
            cache_key,
            ttl or self.ttl['cache'],
            json.dumps(value)
        )
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cache value."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._get_key('cache', key)
        data = await self.client.get(cache_key)
        return json.loads(data) if data else None
    
    async def cache_delete(self, key: str):
        """Delete a cache value."""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._get_key('cache', key)
        await self.client.delete(cache_key)
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if not self._initialized:
            await self.initialize()
        
        info = await self.client.info()
        
        return {
            'used_memory': info.get('used_memory_human', '0'),
            'total_keys': info.get('db0', {}).get('keys', 0),
            'hit_rate': info.get('keyspace_hits', 0) / 
                       (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)),
            'connected_clients': info.get('connected_clients', 0)
        }