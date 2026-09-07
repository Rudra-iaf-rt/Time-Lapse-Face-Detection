# eval/tracking_metrics.py
"""Tracking metrics (MOTA, IDF1, IDSW, FP, FN) when ground truth exists."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from eval.metrics import GROUND_TRUTH_NOT_AVAILABLE


@dataclass
class TrackFrame:
    frame_id: int
    track_id: str
    bbox: Tuple[float, float, float, float]  # x1,y1,x2,y2


def _iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def evaluate_tracking(
    predictions: List[TrackFrame],
    ground_truth: Optional[List[TrackFrame]],
    iou_threshold: float = 0.5,
) -> Dict[str, Any]:
    if ground_truth is None or len(ground_truth) == 0:
        return {
            "status": GROUND_TRUTH_NOT_AVAILABLE,
            "mota": None,
            "idf1": None,
            "id_switches": None,
            "fp": None,
            "fn": None,
            "message": "Provide ground-truth TrackFrame list to compute MOT metrics.",
        }

    gt_by_frame: Dict[int, List[TrackFrame]] = {}
    pr_by_frame: Dict[int, List[TrackFrame]] = {}
    for g in ground_truth:
        gt_by_frame.setdefault(g.frame_id, []).append(g)
    for p in predictions:
        pr_by_frame.setdefault(p.frame_id, []).append(p)

    fp = fn = idsw = matches = 0
    prev_match: Dict[str, str] = {}  # gt_id -> pred_id

    frames = sorted(set(gt_by_frame) | set(pr_by_frame))
    for frame in frames:
        gts = gt_by_frame.get(frame, [])
        preds = pr_by_frame.get(frame, [])
        used_p = set()
        used_g = set()
        pairs: List[Tuple[float, int, int]] = []
        for gi, g in enumerate(gts):
            for pi, p in enumerate(preds):
                pairs.append((_iou(g.bbox, p.bbox), gi, pi))
        pairs.sort(reverse=True)
        frame_matches: List[Tuple[TrackFrame, TrackFrame]] = []
        for iou, gi, pi in pairs:
            if iou < iou_threshold or gi in used_g or pi in used_p:
                continue
            used_g.add(gi)
            used_p.add(pi)
            frame_matches.append((gts[gi], preds[pi]))
            matches += 1

        fn += len(gts) - len(used_g)
        fp += len(preds) - len(used_p)

        for g, p in frame_matches:
            prev = prev_match.get(g.track_id)
            if prev is not None and prev != p.track_id:
                idsw += 1
            prev_match[g.track_id] = p.track_id

    gt_total = len(ground_truth)
    mota = 1.0 - (fn + fp + idsw) / gt_total if gt_total else 0.0

    # Simplified IDF1 approximation from match counts
    idtp = matches
    id_precision = idtp / (idtp + fp) if (idtp + fp) else 0.0
    id_recall = idtp / (idtp + fn) if (idtp + fn) else 0.0
    idf1 = (
        2 * id_precision * id_recall / (id_precision + id_recall)
        if (id_precision + id_recall)
        else 0.0
    )

    return {
        "status": "OK",
        "mota": mota,
        "idf1": idf1,
        "id_switches": idsw,
        "fp": fp,
        "fn": fn,
        "matches": matches,
        "gt_count": gt_total,
        "pred_count": len(predictions),
    }
