"""Evaluation package for multi-camera Re-ID.

Does not fabricate scores. When ground truth is missing, metrics report
GROUND TRUTH NOT AVAILABLE.
"""

__all__ = [
    "metrics",
    "reid_evaluator",
    "tracking_metrics",
    "fusion_metrics",
]
