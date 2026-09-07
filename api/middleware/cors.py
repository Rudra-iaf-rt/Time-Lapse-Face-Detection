# api/middleware/cors.py
"""CORS helpers — origins come from environment, not hardcoded secrets."""

import os
from typing import List


def get_allowed_origins() -> List[str]:
    """Parse CORS_ORIGINS env (comma-separated). Default permissive for local dev only."""
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
