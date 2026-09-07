# Evaluation Framework

## Purpose

Measure tracking, Re-ID, and fusion quality **only when ground truth is available**.

If labels are missing, metrics return:

```text
GROUND TRUTH NOT AVAILABLE
```

No fabricated Rank-1 / MOTA / mAP scores.

## Modules

| Module | Role |
|--------|------|
| `metrics.py` | cosine similarity, AP/mAP helpers |
| `tracking_metrics.py` | MOTA, IDF1, ID switches, FP, FN |
| `reid_evaluator.py` | Rank-1, Rank-5, mAP, similarity distributions |
| `fusion_metrics.py` | Ablation: face / reid / temporal / topology / full |
| `benchmarks/latency_bench.py` | Measured latency + optional CPU/GPU/memory |

## Example

```python
from eval.reid_evaluator import ReidEvaluator
from eval.tracking_metrics import evaluate_tracking

print(ReidEvaluator().evaluate(queries=[], gallery=[], query_labels=None))
print(evaluate_tracking(predictions=[], ground_truth=None))
```

## Benchmarks

```bash
python -m eval.benchmarks.latency_bench
```

Writes machine-generated JSON under `eval/experiments/` when configured.
