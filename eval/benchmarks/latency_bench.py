# eval/benchmarks/latency_bench.py
"""Machine-generated latency / resource benchmarks. Does not invent FPS numbers."""

from __future__ import annotations

import time
import platform
import json
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timezone


def _try_psutil():
    try:
        import psutil

        return psutil
    except ImportError:
        return None


def _gpu_info() -> Dict[str, Any]:
    try:
        import torch

        if torch.cuda.is_available():
            return {
                "cuda_available": True,
                "device_name": torch.cuda.get_device_name(0),
                "device_count": torch.cuda.device_count(),
            }
        return {"cuda_available": False}
    except Exception as exc:
        return {"cuda_available": False, "error": str(exc)}


def time_callable(fn: Callable[[], Any], repeats: int = 10, warmup: int = 2) -> Dict[str, Any]:
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    import statistics

    return {
        "repeats": repeats,
        "latency_ms_mean": statistics.mean(times),
        "latency_ms_stdev": statistics.pstdev(times) if len(times) > 1 else 0.0,
        "latency_ms_min": min(times),
        "latency_ms_max": max(times),
        "samples_ms": times,
    }


def system_snapshot() -> Dict[str, Any]:
    psutil = _try_psutil()
    snap: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "gpu": _gpu_info(),
    }
    if psutil:
        proc = psutil.Process()
        snap["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        snap["memory_rss_mb"] = proc.memory_info().rss / (1024 * 1024)
        snap["memory_percent"] = proc.memory_percent()
    else:
        snap["cpu_percent"] = None
        snap["memory_rss_mb"] = None
        snap["note"] = "Install psutil for CPU/memory samples"
    return snap


def run_pipeline_stage_bench(
    stages: Dict[str, Callable[[], Any]],
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": system_snapshot(),
        "stages": {},
    }
    for name, fn in stages.items():
        try:
            report["stages"][name] = {"status": "OK", **time_callable(fn)}
        except Exception as exc:
            report["stages"][name] = {"status": "ERROR", "error": str(exc)}

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run_pipeline_stage_bench(
        {
            "noop": lambda: None,
            "sleep_1ms": lambda: time.sleep(0.001),
        },
        output_path="eval/experiments/latency_smoke.json",
    )
    print(json.dumps(report, indent=2))
