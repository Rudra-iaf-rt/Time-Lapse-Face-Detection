# api/middleware/security.py
"""Basic production security headers and simple in-memory rate limiting."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse


RATE_LIMIT = int(os.environ.get("API_RATE_LIMIT_PER_MINUTE", "120"))
_WINDOW = 60.0
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


async def security_and_rate_limit(request: Request, call_next):
    # Skip rate limit for health probes and metrics
    path = request.url.path
    if path not in {"/live", "/health", "/ready", "/metrics"}:
        key = _client_key(request)
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > _WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "status_code": 429,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
        q.append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-XSS-Protection"] = "0"
    if os.environ.get("ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
