# api/middleware/metrics_mw.py
"""Record Prometheus request count/latency for non-metrics paths."""

from __future__ import annotations

import time
from starlette.requests import Request

from api.routes.metrics_route import REQUEST_COUNT, REQUEST_LATENCY


async def record_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        endpoint = request.url.path
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(status_code),
        ).inc()
