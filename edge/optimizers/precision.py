# edge/optimizers/precision.py
"""Optional precision / export helpers with safe fallbacks."""

from __future__ import annotations

from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def enable_fp16_if_available(model: Any, device: str) -> Any:
    if device != "cuda":
        logger.info("FP16 skipped — device is %s", device)
        return model
    try:
        return model.half()
    except Exception as exc:
        logger.warning("FP16 enable failed, keeping FP32: %s", exc)
        return model


def try_export_onnx(model: Any, example_input: Any, output_path: str) -> bool:
    try:
        import torch

        torch.onnx.export(
            model,
            example_input,
            output_path,
            input_names=["input"],
            output_names=["output"],
            opset_version=17,
            dynamo=False,
        )
        logger.info("ONNX export written to %s", output_path)
        return True
    except Exception as exc:
        logger.warning("ONNX export disabled/failed: %s", exc)
        return False


def try_tensorrt_engine(onnx_path: str) -> Optional[str]:
    """Attempt TensorRT build. Returns engine path or None — never crashes."""
    try:
        import tensorrt  # noqa: F401
    except Exception:
        logger.info("TensorRT feature disabled / fallback to PyTorch")
        return None
    logger.info(
        "TensorRT present but engine build is opt-in; returning None (not mandatory). onnx=%s",
        onnx_path,
    )
    return None
