# eval/reid_evaluator.py
"""Re-ID evaluation: Rank-1, Rank-5, mAP, cosine similarity distributions."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Any, Tuple
import numpy as np

from eval.metrics import (
    GROUND_TRUTH_NOT_AVAILABLE,
    cosine_similarity,
    mean_average_precision,
    rank_k_hit,
    summarize_similarities,
)


class ReidEvaluator:
    """
    Evaluate gallery retrieval.

    queries: list of (query_id, embedding)
    gallery: list of (gallery_id, embedding, identity_label)
    query_labels: map query_id -> identity_label (ground truth)
    """

    def evaluate(
        self,
        queries: Sequence[Tuple[str, np.ndarray]],
        gallery: Sequence[Tuple[str, np.ndarray, str]],
        query_labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not query_labels:
            return {
                "status": GROUND_TRUTH_NOT_AVAILABLE,
                "rank1": None,
                "rank5": None,
                "mAP": None,
                "cosine_similarity": None,
                "message": "Provide query_labels (global_id ground truth) to score Re-ID.",
            }

        ranked_rels: List[List[int]] = []
        sims_pos: List[float] = []
        sims_neg: List[float] = []
        rank1s: List[float] = []
        rank5s: List[float] = []

        for qid, qemb in queries:
            label = query_labels.get(qid)
            if label is None:
                continue
            scored: List[Tuple[float, str]] = []
            for gid, gemb, glabel in gallery:
                if gid == qid:
                    continue
                sim = cosine_similarity(qemb, gemb)
                scored.append((sim, glabel))
                if glabel == label:
                    sims_pos.append(sim)
                else:
                    sims_neg.append(sim)
            scored.sort(key=lambda x: x[0], reverse=True)
            relevance = [1 if glabel == label else 0 for _, glabel in scored]
            ranked_rels.append(relevance)
            rank1s.append(rank_k_hit(relevance, 1))
            rank5s.append(rank_k_hit(relevance, 5))

        if not ranked_rels:
            return {
                "status": GROUND_TRUTH_NOT_AVAILABLE,
                "rank1": None,
                "rank5": None,
                "mAP": None,
                "message": "No query/gallery pairs with labels could be evaluated.",
            }

        return {
            "status": "OK",
            "rank1": float(np.mean(rank1s)),
            "rank5": float(np.mean(rank5s)),
            "mAP": mean_average_precision(ranked_rels),
            "cosine_similarity": {
                "positive": summarize_similarities(sims_pos),
                "negative": summarize_similarities(sims_neg),
            },
            "num_queries_evaluated": len(ranked_rels),
        }


# CLI helper
if __name__ == "__main__":
    print(
        ReidEvaluator().evaluate(
            queries=[],
            gallery=[],
            query_labels=None,
        )
    )
