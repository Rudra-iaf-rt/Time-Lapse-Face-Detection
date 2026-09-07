# api/middleware/logging.py
"""HTTP request logging middleware."""

import logging
import time
from starlette.requests import Request

logger = logging.getLogger("api.access")


async def log_requests(request: Request, call_next):
    """Log method, path, status, and latency. Never logs embeddings or secrets."""
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        status = getattr(response, "status_code", 500) if response is not None else 500
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            status,
            elapsed_ms,
        )
