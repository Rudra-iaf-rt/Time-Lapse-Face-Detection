# api/routes/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime

from ..dependencies.database import get_redis_manager
from database.redis_manager import RedisManager
from websocket.connection_manager import ConnectionManager
from websocket.event_broadcaster import EventBroadcaster
from websocket.message_handler import MessageHandler

router = APIRouter()

# Connection manager
manager = ConnectionManager()
event_broadcaster = None
message_handler = None

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    """
    WebSocket endpoint for real-time updates.
    
    Args:
        websocket: WebSocket connection
        client_id: Client identifier
    """
    global event_broadcaster, message_handler
    
    # Initialize components if not already done
    if event_broadcaster is None:
        redis = await get_redis_manager()
        event_broadcaster = EventBroadcaster(redis, manager)
        message_handler = MessageHandler(manager, event_broadcaster)
    
    # Accept connection
    await manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await manager.send_message(client_id, {
            'type': 'connection',
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # Subscribe to events
        await event_broadcaster.subscribe_client(client_id, ['all'])
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                response = await message_handler.handle_message(message, client_id)
                
                if response:
                    await manager.send_message(client_id, response)
                    
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    'type': 'error',
                    'message': 'Invalid JSON format',
                    'timestamp': datetime.now().isoformat()
                })
            
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
        await event_broadcaster.unsubscribe_client(client_id)
        
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(client_id)

@router.get("/websocket/status")
async def websocket_status():
    """
    Get WebSocket connection status.
    """
    return {
        'active_connections': manager.get_connection_count(),
        'clients': manager.get_client_ids(),
        'timestamp': datetime.now().isoformat()
    }