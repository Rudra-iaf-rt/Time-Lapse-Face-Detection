# api/routes/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import json
import logging
from datetime import datetime

from api.dependencies.database import get_managers_raw
from websocket.connection_manager import ConnectionManager
from websocket.event_broadcaster import EventBroadcaster
from websocket.message_handler import MessageHandler

logger = logging.getLogger(__name__)

router = APIRouter()

manager = ConnectionManager()
event_broadcaster: Optional[EventBroadcaster] = None
message_handler: Optional[MessageHandler] = None


def _ensure_handlers() -> tuple[EventBroadcaster, MessageHandler]:
    global event_broadcaster, message_handler
    if event_broadcaster is None or message_handler is None:
        managers = get_managers_raw()
        redis = managers.get("redis")
        if redis is None:
            raise RuntimeError("Redis manager not initialized")
        event_broadcaster = EventBroadcaster(redis, manager)
        message_handler = MessageHandler(manager, event_broadcaster)
    return event_broadcaster, message_handler


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time structured events."""
    try:
        broadcaster, handler = _ensure_handlers()
    except Exception as exc:
        await websocket.accept()
        await websocket.send_json(
            {
                "event": "error",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": f"WebSocket backend unavailable: {exc}",
            }
        )
        await websocket.close(code=1013)
        return

    await manager.connect(websocket, client_id)

    try:
        await manager.send_message(
            client_id,
            {
                "event": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )
        await broadcaster.subscribe_client(client_id, ["all"])

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_message(
                    client_id,
                    {
                        "event": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    },
                )
                continue

            response = await handler.handle_message(message, client_id)
            if response:
                await manager.send_message(client_id, response)

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
        try:
            await broadcaster.unsubscribe_client(client_id)
        except Exception as exc:
            logger.error("Unsubscribe failed for %s: %s", client_id, exc)
    except Exception as exc:
        logger.error("WebSocket error for %s: %s", client_id, exc, exc_info=True)
        await manager.disconnect(client_id)


@router.get("/websocket/status")
async def websocket_status():
    return {
        "active_connections": manager.get_connection_count(),
        "clients": manager.get_client_ids(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
