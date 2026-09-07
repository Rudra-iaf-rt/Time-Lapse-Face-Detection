# edge/devices/capability.py
"""Detect available compute backends without requiring Jetson/TensorRT."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class DeviceCapabilities:
    cpu: bool = True
    cuda: bool = False
    cuda_device_name: Optional[str] = None
    onnxruntime: bool = False
    tensorrt: bool = False
    preferred_backend: str = "cpu"
    notes: str = ""


def detect_capabilities() -> DeviceCapabilities:
    caps = DeviceCapabilities()
    notes = []

    try:
        import torch

        if torch.cuda.is_available():
            caps.cuda = True
            caps.cuda_device_name = torch.cuda.get_device_name(0)
            caps.preferred_backend = "cuda"
            notes.append("CUDA available")
        else:
            notes.append("CUDA not available — using CPU")
    except Exception as exc:
        notes.append(f"PyTorch check failed: {exc}")

    try:
        import onnxruntime as ort  # noqa: F401

        caps.onnxruntime = True
        notes.append("ONNX Runtime available")
    except Exception:
        notes.append("ONNX Runtime not installed — feature disabled")

    try:
        import tensorrt  # noqa: F401

        caps.tensorrt = True
        notes.append("TensorRT available (optional)")
    except Exception:
        notes.append("TensorRT unavailable — fallback to PyTorch/ONNX")

    if caps.tensorrt and caps.cuda:
        # Prefer CUDA torch by default; TensorRT remains opt-in
        notes.append("TensorRT detected but not mandatory; enable explicitly in config")

    caps.notes = "; ".join(notes)
    return caps


def select_backend(prefer_trt: bool = False, prefer_onnx: bool = False) -> str:
    caps = detect_capabilities()
    if prefer_trt and caps.tensorrt and caps.cuda:
        return "tensorrt"
    if prefer_onnx and caps.onnxruntime:
        return "onnx"
    if caps.cuda:
        return "cuda"
    return "cpu"


if __name__ == "__main__":
    print(json.dumps(asdict(detect_capabilities()), indent=2))
