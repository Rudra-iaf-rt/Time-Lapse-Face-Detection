from __future__ import annotations

import time
from typing import Any, Dict

import cv2


def _open_source(source_uri: str) -> cv2.VideoCapture:
    if str(source_uri).isdigit():
        return cv2.VideoCapture(int(source_uri))
    return cv2.VideoCapture(str(source_uri))


def test_camera_source(source_uri: str, sample_frames: int = 5) -> Dict[str, Any]:
    started = time.perf_counter()
    cap = _open_source(source_uri)
    result: Dict[str, Any] = {
        "ok": False,
        "source_uri": source_uri,
        "frames_read": 0,
        "fps": None,
        "width": None,
        "height": None,
        "latency_ms": None,
        "error": None,
    }

    try:
        if not cap.isOpened():
            result["error"] = "Unable to open source"
            return result

        result["fps"] = cap.get(cv2.CAP_PROP_FPS) or None
        result["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        result["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None

        frames = 0
        for _ in range(max(1, sample_frames)):
            ok, frame = cap.read()
            if ok and frame is not None:
                frames += 1
            else:
                break

        result["frames_read"] = frames
        result["ok"] = frames > 0
        if not result["ok"]:
            result["error"] = "Source opened but no frames could be read"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        cap.release()
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

    return result