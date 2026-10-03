"""Per-IP rate limiting for /chat (PRD risk: spam leads). Use a Redis storage URI when
running more than one replica, otherwise each replica counts separately."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from estimator_agent.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_settings().rate_limit_storage_uri,
)


def chat_limit() -> str:
    return get_settings().rate_limit_chat
