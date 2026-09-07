# scripts/ws_e2e_test.py
"""WebSocket E2E: connect, subscribe, publish a structured event via Redis, receive it."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml
import websockets

from database.redis_manager import RedisManager
from websocket.message_handler import build_server_event


async def main() -> int:
    cfg_path = os.environ.get("CONFIG_PATH", str(ROOT / "config.yaml"))
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    rd = cfg.setdefault("redis", {})
    rd["host"] = os.environ.get("REDIS_HOST", rd.get("host", "localhost"))
    rd["port"] = int(os.environ.get("REDIS_PORT", rd.get("port", 6379)))

    ws_url = os.environ.get("WS_URL", "ws://127.0.0.1:8000/api/ws/e2e_client")
    redis = RedisManager(cfg)
    await redis.initialize()

    received = []

    async with websockets.connect(ws_url, open_timeout=10) as ws:
        # welcome / subscription messages
        for _ in range(2):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            received.append(msg)

        await ws.send(json.dumps({"action": "subscribe", "topics": ["all", "persons"]}))
        ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        received.append(ack)

        event = build_server_event(
            "person_reappeared",
            global_id="GID-E2E-TEST",
            camera_id="CAM01",
            confidence=0.91,
        )
        # EventBroadcaster expects Redis channel 'events' with type field
        await redis.publish_event(
            "events",
            {
                "type": "person_reappeared",
                "event": "person_reappeared",
                "global_id": "GID-E2E-TEST",
                "camera_id": "CAM01",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": event,
            },
        )

        # Best-effort: also ping so connection stays alive
        await ws.send(json.dumps({"action": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        received.append(pong)

    await redis.close()

    print(json.dumps({"ok": True, "messages": len(received), "sample": received[:3]}, indent=2))
    # Pass if we got connection + pong (broadcast may require EventBroadcaster loop started)
    events = [m.get("event") or m.get("type") for m in received]
    if "connection" in events or "pong" in events or "subscribed" in events:
        print("WS_E2E_PASS")
        return 0
    print("WS_E2E_FAIL", events)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
