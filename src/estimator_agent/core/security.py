"""Admin authentication primitives. v1 = shared API key in a header; swap for OAuth/JWT later.
The FastAPI dependency lives in api/deps.py so it can use the app's own settings."""

from __future__ import annotations

import secrets


def verify_admin_key(provided: str | None, expected: str) -> bool:
    # constant-time compare to avoid timing attacks
    return bool(provided) and secrets.compare_digest(provided or "", expected)
