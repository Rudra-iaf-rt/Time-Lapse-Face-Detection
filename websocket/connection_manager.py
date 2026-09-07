# websocket/connection_manager.py
from fastapi import WebSocket
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manage WebSocket connections.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
        self.subscriptions: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new connection."""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                'connected_at': datetime.now(),
                'last_activity': datetime.now()
            }
            self.subscriptions[client_id] = []
        
        logger.info(f"Client {client_id} connected")
    
    async def disconnect(self, client_id: str):
        """Disconnect a client."""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            if client_id in self.subscriptions:
                del self.subscriptions[client_id]
        
        logger.info(f"Client {client_id} disconnected")
    
    async def send_message(self, client_id: str, message: Dict):
        """Send a message to a specific client."""
        if client_id not in self.active_connections:
            return False
        
        try:
            await self.active_connections[client_id].send_json(message)
            
            # Update last activity
            if client_id in self.connection_metadata:
                self.connection_metadata[client_id]['last_activity'] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            return False
    
    async def broadcast(self, message: Dict, exclude: List[str] = None):
        """Broadcast a message to all connected clients."""
        exclude = exclude or []
        
        tasks = []
        for client_id in self.active_connections:
            if client_id not in exclude:
                tasks.append(self.send_message(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_subscribers(self, topic: str, message: Dict):
        """Broadcast to subscribers of a topic."""
        tasks = []
        for client_id, topics in self.subscriptions.items():
            if topic in topics or 'all' in topics:
                tasks.append(self.send_message(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_client_ids(self) -> List[str]:
        """Get list of connected client IDs."""
        return list(self.active_connections.keys())
    
    def get_connection_metadata(self, client_id: str) -> Optional[Dict]:
        """Get metadata for a connection."""
        return self.connection_metadata.get(client_id)
    
    async def subscribe(self, client_id: str, topics: List[str]):
        """Subscribe a client to topics."""
        async with self._lock:
            if client_id not in self.subscriptions:
                self.subscriptions[client_id] = []
            
            for topic in topics:
                if topic not in self.subscriptions[client_id]:
                    self.subscriptions[client_id].append(topic)
    
    async def unsubscribe(self, client_id: str, topics: List[str]):
        """Unsubscribe a client from topics."""
        async with self._lock:
            if client_id in self.subscriptions:
                for topic in topics:
                    if topic in self.subscriptions[client_id]:
                        self.subscriptions[client_id].remove(topic)