"""Outbound notifications to the owner. Email via Resend (or console in dev);
WhatsApp via wa.me deep links (no Business API approval needed for v1)."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import quote

import httpx

from estimator_agent.core.config import Settings
from estimator_agent.core.logging import get_logger

log = get_logger(__name__)


def whatsapp_link(phone_e164_digits: str, text: str) -> str:
    return f"https://wa.me/{phone_e164_digits}?text={quote(text)}"


class Notifier(Protocol):
    async def send_email(self, to: str, subject: str, body: str) -> str: ...


class ConsoleNotifier:
    """Dev/test: logs instead of sending."""

    async def send_email(self, to: str, subject: str, body: str) -> str:
        log.info("email_dry_run", to=to, subject=subject, body=body[:500])
        return "console-dry-run"


class ResendNotifier:
    def __init__(self, api_key: str, sender: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = api_key
        self._from = sender
        self._client = client or httpx.AsyncClient(timeout=10)

    async def send_email(self, to: str, subject: str, body: str) -> str:
        resp = await self._client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self._key}"},
            json={"from": self._from, "to": [to], "subject": subject, "text": body},
        )
        resp.raise_for_status()
        return str(resp.json().get("id", ""))


def build_notifier(settings: Settings) -> Notifier:
    if settings.email_provider == "resend" and settings.resend_api_key:
        return ResendNotifier(settings.resend_api_key.get_secret_value(), settings.email_from)
    return ConsoleNotifier()
