# eval/metrics.py
"""Shared metric helpers — real math only, no invented accuracy."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import numpy as np


GROUND_TRUTH_NOT_AVAILABLE = "GROUND TRUTH NOT AVAILABLE"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def average_precision(ranked_relevance: Sequence[int]) -> float:
    """ranked_relevance: sequence of 0/1 in rank order."""
    hits = 0
    sum_prec = 0.0
    for i, rel in enumerate(ranked_relevance, start=1):
        if rel:
            hits += 1
            sum_prec += hits / i
    if hits == 0:
        return 0.0
    return sum_prec / hits


def mean_average_precision(all_ranked: List[Sequence[int]]) -> Optional[float]:
    if not all_ranked:
        return None
    return float(np.mean([average_precision(r) for r in all_ranked]))


def rank_k_hit(ranked_relevance: Sequence[int], k: int) -> float:
    return 1.0 if any(ranked_relevance[:k]) else 0.0


def summarize_similarities(values: Sequence[float]) -> Dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return {"count": 0}
    return {
        "count": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
    }
