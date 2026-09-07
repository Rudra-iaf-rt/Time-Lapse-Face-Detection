# websocket/message_handler.py
"""Parse and handle inbound WebSocket client messages."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from websocket.connection_manager import ConnectionManager
from websocket.event_broadcaster import EventBroadcaster

logger = logging.getLogger(__name__)

ALLOWED_CLIENT_ACTIONS = {
    "ping",
    "subscribe",
    "unsubscribe",
    "get_status",
}

ALLOWED_EVENT_TOPICS = {
    "all",
    "persons",
    "cameras",
    "tracks",
    "alerts",
    "crowd",
    "person_detected",
    "identity_matched",
    "person_reappeared",
    "person_lost",
    "anomaly_detected",
    "camera_status",
    "crowd_update",
}


class MessageHandler:
    """Handle structured client messages. Reject malformed payloads."""

    def __init__(self, manager: ConnectionManager, broadcaster: EventBroadcaster):
        self.manager = manager
        self.broadcaster = broadcaster

    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict]:
        if not isinstance(message, dict):
            return self._error("Message must be a JSON object")

        action = message.get("action") or message.get("type")
        if not action or not isinstance(action, str):
            return self._error("Missing action/type")

        action = action.strip().lower()
        if action not in ALLOWED_CLIENT_ACTIONS:
            return self._error(f"Unsupported action: {action}")

        if action == "ping":
            return {
                "event": "pong",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "client_id": client_id,
            }

        if action == "subscribe":
            topics = self._normalize_topics(message.get("topics") or message.get("channels"))
            if topics is None:
                return self._error("topics must be a list of allowed topic strings")
            await self.broadcaster.subscribe_client(client_id, topics)
            return {
                "event": "subscribed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "topics": topics,
                "client_id": client_id,
            }

        if action == "unsubscribe":
            topics = self._normalize_topics(message.get("topics") or message.get("channels"))
            if topics is None:
                # unsubscribe all
                await self.broadcaster.unsubscribe_client(client_id, None)
                return {
                    "event": "unsubscribed",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "topics": ["all"],
                    "client_id": client_id,
                }
            await self.broadcaster.unsubscribe_client(client_id, topics)
            return {
                "event": "unsubscribed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "topics": topics,
                "client_id": client_id,
            }

        if action == "get_status":
            return {
                "event": "status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "active_connections": self.manager.get_connection_count(),
                "client_id": client_id,
                "subscriptions": self.manager.subscriptions.get(client_id, []),
            }

        return self._error(f"Unhandled action: {action}")

    def _normalize_topics(self, topics: Any) -> Optional[List[str]]:
        if topics is None:
            return None
        if isinstance(topics, str):
            topics = [topics]
        if not isinstance(topics, list) or not all(isinstance(t, str) for t in topics):
            return None
        cleaned = []
        for t in topics:
            t = t.strip().lower()
            if t not in ALLOWED_EVENT_TOPICS:
                logger.warning("Rejecting unknown topic: %s", t)
                continue
            cleaned.append(t)
        return cleaned

    @staticmethod
    def _error(message: str) -> Dict:
        return {
            "event": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message,
        }


def build_server_event(
    event: str,
    *,
    global_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build a structured outbound event payload."""
    payload: Dict[str, Any] = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if global_id is not None:
        payload["global_id"] = global_id
    if camera_id is not None:
        payload["camera_id"] = camera_id
    payload.update(extra)
    return payload
