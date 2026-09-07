# edge/pipeline/metadata_emitter.py
"""Emit compact metadata events; buffer when network is down."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class EdgeEvent:
    camera_id: str
    global_id: str
    timestamp: str
    event: str
    confidence: float

    def to_dict(self) -> Dict:
        return asdict(self)


class MetadataEmitter:
    def __init__(
        self,
        send_fn: Optional[Callable[[Dict], bool]] = None,
        buffer_path: str = "edge/monitoring/event_buffer.jsonl",
        max_buffer: int = 1000,
    ):
        self.send_fn = send_fn
        self.buffer_path = Path(buffer_path)
        self.buffer_path.parent.mkdir(parents=True, exist_ok=True)
        self.buffer: Deque[Dict] = deque(maxlen=max_buffer)

    def emit(
        self,
        camera_id: str,
        global_id: str,
        event: str,
        confidence: float,
    ) -> bool:
        payload = EdgeEvent(
            camera_id=camera_id,
            global_id=global_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            confidence=confidence,
        ).to_dict()

        ok = False
        if self.send_fn is not None:
            try:
                ok = bool(self.send_fn(payload))
            except Exception as exc:
                logger.warning("Send failed, buffering event: %s", exc)
                ok = False

        if not ok:
            self.buffer.append(payload)
            with self.buffer_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        return ok

    def flush(self) -> int:
        """Attempt to flush buffered events. Returns number sent."""
        if self.send_fn is None:
            return 0
        sent = 0
        pending = list(self.buffer)
        self.buffer.clear()
        for item in pending:
            try:
                if self.send_fn(item):
                    sent += 1
                else:
                    self.buffer.append(item)
            except Exception:
                self.buffer.append(item)
                break
        return sent
