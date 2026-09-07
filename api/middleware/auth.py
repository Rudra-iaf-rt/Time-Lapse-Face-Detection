# api/middleware/auth.py
"""JWT extraction helpers used by route dependencies."""

from fastapi import Request
from typing import Optional


def extract_bearer_token(request: Request) -> Optional[str]:
    """Return raw JWT from Authorization: Bearer <token>, or None."""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
