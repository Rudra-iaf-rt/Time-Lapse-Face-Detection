from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_SHARED_MODEL = None
_SHARED_EXTRACTOR = None
_SHARED_STORE = None


def _get_shared() -> tuple[Any, Any, Any]:
    global _SHARED_MODEL, _SHARED_EXTRACTOR, _SHARED_STORE
    if _SHARED_STORE is None:
        from database.identity_store import IdentityStore

        _SHARED_STORE = IdentityStore()
    if _SHARED_EXTRACTOR is None:
        from reid.feature_extractor import FeatureExtractor

        _SHARED_EXTRACTOR = FeatureExtractor(device="cpu")
    if _SHARED_MODEL is None:
        from ultralytics import YOLO

        _SHARED_MODEL = YOLO("yolov8n.pt")
    return _SHARED_MODEL, _SHARED_EXTRACTOR, _SHARED_STORE


class CameraRuntimeManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runtimes: Dict[str, Dict[str, Any]] = {}

    def start(self, camera_id: Any, source_uri: str, roi: Optional[list[int]] = None) -> Dict[str, Any]:
        key = str(camera_id)
        with self._lock:
            existing = self._runtimes.get(key)
            if existing and existing.get("running"):
                return self.get_status(camera_id)

            output_dir = Path("results") / f"runtime_cam{camera_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            status: Dict[str, Any] = {
                "_events": RUNTIME_EVENT_QUEUE,
                "camera_id": camera_id,
                "source_uri": source_uri,
                "running": True,
                "started_at": time.time(),
                "last_frame_at": None,
                "frames_read": 0,
                "fps": None,
                "width": None,
                "height": None,
                "error": None,
                "last_global_ids": [],
            }

            model, extractor, store = _get_shared()
            from tracker.global_tracker import CameraWorker

            worker = CameraWorker(
                source=source_uri,
                camera_id=int(camera_id) if str(camera_id).isdigit() else camera_id,
                store=store,
                extractor=extractor,
                yolo_model=model,
                output_dir=str(output_dir),
                conf=0.35,
                promote_every_n=30,
                save_video=False,
                save_crops=True,
                device="cpu",
                roi=roi,
            )
            worker.runtime_status = status
            status["worker"] = worker
            self._runtimes[key] = status

        thread = threading.Thread(
            target=worker.run_sync,
            daemon=True,
            name=f"camera-reid-runtime-{key}",
        )
        status["_thread"] = thread
        thread.start()
        return self.get_status(camera_id)

    def stop(self, camera_id: Any) -> Dict[str, Any]:
        key = str(camera_id)
        with self._lock:
            status = self._runtimes.get(key)
            if not status:
                return {"camera_id": camera_id, "running": False, "message": "Camera not running"}
            worker = status.get("worker")
            if worker is not None:
                worker.running = False
            stop_event = status.get("_stop")
            if stop_event is not None:
                stop_event.set()
            status["running"] = False
        return self.get_status(camera_id)

    def get_status(self, camera_id: Any) -> Dict[str, Any]:
        key = str(camera_id)
        with self._lock:
            status = self._runtimes.get(key)
            if not status:
                return {"camera_id": camera_id, "running": False}
            clean = {k: v for k, v in status.items() if not str(k).startswith("_") and k != "worker"}
            return clean

    def list_statuses(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [self.get_status(cid) for cid in self._runtimes]


RUNTIME_EVENT_QUEUE = queue.Queue()
camera_runtime = CameraRuntimeManager()