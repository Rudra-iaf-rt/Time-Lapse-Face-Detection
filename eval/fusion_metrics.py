# eval/fusion_metrics.py
"""Ablation framework for multimodal identity fusion — no fabricated results."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Any, Sequence
from dataclasses import dataclass
import numpy as np

from eval.metrics import GROUND_TRUTH_NOT_AVAILABLE, cosine_similarity


ABLATION_MODES = [
    "face_only",
    "reid_only",
    "face_reid",
    "face_reid_temporal",
    "face_reid_topology",
    "full_fusion",
]


@dataclass
class FusionSample:
    global_id_true: str
    face_sim: Optional[float] = None
    reid_sim: Optional[float] = None
    temporal_score: Optional[float] = None
    topology_score: Optional[float] = None
    appearance_score: Optional[float] = None


def score_mode(sample: FusionSample, mode: str, weights: Dict[str, float]) -> Optional[float]:
    parts: List[tuple[str, Optional[float]]] = []
    if mode == "face_only":
        parts = [("face", sample.face_sim)]
    elif mode == "reid_only":
        parts = [("reid", sample.reid_sim)]
    elif mode == "face_reid":
        parts = [("face", sample.face_sim), ("reid", sample.reid_sim)]
    elif mode == "face_reid_temporal":
        parts = [
            ("face", sample.face_sim),
            ("reid", sample.reid_sim),
            ("temporal", sample.temporal_score),
        ]
    elif mode == "face_reid_topology":
        parts = [
            ("face", sample.face_sim),
            ("reid", sample.reid_sim),
            ("spatial", sample.topology_score),
        ]
    elif mode == "full_fusion":
        parts = [
            ("face", sample.face_sim),
            ("reid", sample.reid_sim),
            ("appearance", sample.appearance_score),
            ("temporal", sample.temporal_score),
            ("spatial", sample.topology_score),
        ]
    else:
        raise ValueError(f"Unknown mode: {mode}")

    available = [(k, v) for k, v in parts if v is not None]
    if not available:
        return None
    wsum = sum(weights.get(k, 1.0) for k, _ in available)
    if wsum <= 0:
        return None
    return sum(weights.get(k, 1.0) * v for k, v in available) / wsum


def run_ablation(
    samples: Sequence[FusionSample],
    threshold: float = 0.65,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    if not samples:
        return {
            "status": GROUND_TRUTH_NOT_AVAILABLE,
            "message": "No labeled fusion samples provided.",
            "modes": {},
        }

    weights = weights or {
        "face": 0.35,
        "reid": 0.30,
        "appearance": 0.10,
        "temporal": 0.10,
        "spatial": 0.15,
    }

    results: Dict[str, Any] = {}
    for mode in ABLATION_MODES:
        scores = [score_mode(s, mode, weights) for s in samples]
        valid = [s for s in scores if s is not None]
        if not valid:
            results[mode] = {
                "status": GROUND_TRUTH_NOT_AVAILABLE,
                "message": f"No usable signals for mode {mode}",
            }
            continue
        # Without explicit accept/reject labels beyond score, report distribution only
        results[mode] = {
            "status": "OK",
            "count": len(valid),
            "mean_score": float(np.mean(valid)),
            "above_threshold_rate": float(np.mean([1.0 if s >= threshold else 0.0 for s in valid])),
            "threshold": threshold,
            "note": "above_threshold_rate is score distribution vs threshold, not claimed accuracy without GT match labels.",
        }

    return {"status": "OK", "modes": results, "weights": weights}
