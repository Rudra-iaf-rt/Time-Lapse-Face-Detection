# websocket/event_broadcaster.py
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from database.redis_manager import RedisManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

class EventBroadcaster:
    """
    Broadcast events to WebSocket clients.
    """
    
    def __init__(self, redis: RedisManager, manager: ConnectionManager):
        self.redis = redis
        self.manager = manager
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the event broadcaster."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info("Event broadcaster started")
    
    async def stop(self):
        """Stop the event broadcaster."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event broadcaster stopped")
    
    async def _broadcast_loop(self):
        """Main broadcast loop."""
        while self._running:
            try:
                # Subscribe to Redis channels
                pubsub = await self.redis.subscribe_events('events')
                
                while self._running:
                    try:
                        message = await pubsub.get_message(timeout=1.0)
                        if message and message['type'] == 'message':
                            data = json.loads(message['data'])
                            await self._broadcast_event(data)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error in broadcast loop: {e}")
                        await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")
                await asyncio.sleep(5)
    
    async def _broadcast_event(self, event: Dict):
        """Broadcast an event to clients."""
        event_type = event.get('type', 'unknown')
        
        # Add timestamp if not present
        if 'timestamp' not in event:
            event['timestamp'] = datetime.now().isoformat()
        
        # Broadcast to appropriate clients
        message = {
            'type': 'event',
            'event': event
        }
        
        # Broadcast based on event type
        if event_type in ['person_update', 'new_person']:
            await self.manager.broadcast_to_subscribers('persons', message)
        
        elif event_type in ['camera_state', 'occupancy_update']:
            await self.manager.broadcast_to_subscribers('cameras', message)
        
        elif event_type in ['anomaly', 'alert']:
            await self.manager.broadcast_to_subscribers('alerts', message)
        
        elif event_type in ['track_update', 'detection']:
            await self.manager.broadcast_to_subscribers('tracks', message)
        
        else:
            # Default: broadcast to all
            await self.manager.broadcast(message)
    
    async def publish_event(self, event_type: str, data: Dict):
        """
        Publish an event to Redis for broadcasting.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.redis.publish_event('events', event)
    
    async def subscribe_client(self, client_id: str, topics: List[str]):
        """Subscribe a client to topics."""
        await self.manager.subscribe(client_id, topics)
        
        # Send subscription confirmation
        await self.manager.send_message(client_id, {
            'type': 'subscription',
            'status': 'subscribed',
            'topics': topics,
            'timestamp': datetime.now().isoformat()
        })
    
    async def unsubscribe_client(self, client_id: str, topics: List[str] = None):
        """Unsubscribe a client from topics."""
        if topics:
            await self.manager.unsubscribe(client_id, topics)
        else:
            # Unsubscribe from all
            if client_id in self.manager.subscriptions:
                self.manager.subscriptions[client_id] = []
        
        # Send unsubscription confirmation
        await self.manager.send_message(client_id, {
            'type': 'subscription',
            'status': 'unsubscribed',
            'topics': topics or ['all'],
            'timestamp': datetime.now().isoformat()
        })