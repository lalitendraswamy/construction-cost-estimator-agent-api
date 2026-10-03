"""Contact tools: get_available_slots, book_meeting, notify_owner.

book_meeting and notify_owner have side effects, so each calls `interrupt()` to get an
explicit "yes" from the user first (PRD F6: tools with side effects + human confirm).
On resume, LangGraph re-runs the tool from the top and `interrupt()` returns the answer.
=> Never put a side effect BEFORE the interrupt() call.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt

from estimator_agent.agent.context import AgentContext
from estimator_agent.core.exceptions import ConflictError
from estimator_agent.domain import ContactChannel, Estimate, Language, Lead, ProjectSpec
from estimator_agent.services.formatting import format_lakhs
from estimator_agent.services.notifications import whatsapp_link

IST = timezone(timedelta(hours=5, minutes=30), "IST")  # no DST, no tzdata needed
BUSINESS_HOURS = range(10, 18)  # slot start hours
_PHONE_RE = re.compile(r"^(?:\+?91)?([6-9]\d{9})$")
_YES = {
    "yes",
    "y",
    "ok",
    "okay",
    "sure",
    "confirm",
    "avunu",
    "sare",
    "haa",
    "haan",
    "ha",
    "ji",
    "అవును",
    "సరే",
    "हाँ",
    "हां",
    "जी",
}


def normalise_phone(raw: str) -> str | None:
    m = _PHONE_RE.match(re.sub(r"[\s\-()]", "", raw))
    return f"91{m.group(1)}" if m else None


def is_affirmative(answer: Any) -> bool:
    if isinstance(answer, bool):
        return answer
    if isinstance(answer, dict):
        return bool(answer.get("confirmed"))
    # Split on spaces/punctuation, not \w: Telugu vowel signs are not \w characters.
    first = re.split(r"[\s,.!?;:]+", str(answer).strip().lower())[0]
    return first in _YES


def require_confirmation(action: str, details: dict[str, Any]) -> bool:
    answer = interrupt({"type": "confirm_action", "action": action, "details": details})
    return is_affirmative(answer)


def build_contact_tools(
    ctx: AgentContext,
    *,
    thread_id: str,
    language: Language,
    spec: ProjectSpec | None,
    estimate: Estimate | None,
) -> list[BaseTool]:
    settings = ctx.settings

    async def _save_lead(lead: Lead) -> None:
        await ctx.leads.upsert_for_thread(
            thread_id, lead, language=language.value, spec=spec, estimate=estimate
        )

    @tool("get_available_slots")
    async def get_available_slots(days_ahead: int = 3) -> list[str]:
        """Free one-hour slots (Mon-Sat, 10:00-18:00 IST) for the next `days_ahead` days."""
        today = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = today + timedelta(days=1), today + timedelta(days=1 + min(days_ahead, 7))
        taken = await ctx.bookings.booked_slots(start, end)
        slots: list[str] = []
        day = start
        while day < end:
            if day.weekday() != 6:  # closed Sunday
                for h in BUSINESS_HOURS:
                    slot = day.replace(hour=h)
                    if slot not in taken:
                        slots.append(slot.isoformat())
            day += timedelta(days=1)
        return slots

    @tool("book_meeting")
    async def book_meeting(name: str, phone: str, slot_iso: str, channel: ContactChannel) -> str:
        """Book a call/visit slot with the owner. Asks the user to confirm first."""
        phone_n = normalise_phone(phone)
        if phone_n is None:
            return "Invalid Indian mobile number; ask the user to re-check it."
        slot = datetime.fromisoformat(slot_iso)
        if not require_confirmation(
            "book_meeting", {"name": name, "phone": phone_n, "slot": slot_iso, "channel": channel}
        ):
            return "User did not confirm. Nothing was booked."
        try:
            booking_id = await ctx.bookings.create(thread_id=thread_id, slot=slot, mode=channel)
        except ConflictError:
            return "That slot was just taken; offer other slots."
        await _save_lead(
            Lead(
                name=name,
                phone=phone_n,
                channel=channel,
                preferred_slot=slot_iso,
                booking_id=booking_id,
            )
        )
        return f"Booked. booking_id={booking_id}"

    @tool("notify_owner")
    async def notify_owner(name: str, phone: str, channel: ContactChannel, note: str = "") -> str:
        """Send the lead summary (with the estimate) to the owner. Asks the user to confirm first."""
        phone_n = normalise_phone(phone)
        if phone_n is None:
            return "Invalid Indian mobile number; ask the user to re-check it."
        if not require_confirmation(
            "notify_owner", {"name": name, "phone": phone_n, "channel": channel, "note": note}
        ):
            return "User did not confirm. Nothing was sent."
        summary = _lead_summary(name, phone_n, channel, note, spec, estimate)
        await ctx.notifier.send_email(settings.owner_email, f"New estimator lead: {name}", summary)
        await _save_lead(Lead(name=name, phone=phone_n, channel=channel, owner_notified=True))
        link = whatsapp_link(
            settings.owner_whatsapp, f"Hi {settings.owner_name}, I'm {name}. {note}"
        )
        return f"Owner notified. WhatsApp link for the user: {link}"

    return [get_available_slots, book_meeting, notify_owner]


def _lead_summary(
    name: str,
    phone: str,
    channel: str,
    note: str,
    spec: ProjectSpec | None,
    estimate: Estimate | None,
) -> str:
    lines = [f"Name: {name}", f"Phone: +{phone}", f"Channel: {channel}", f"Note: {note or '-'}"]
    if spec:
        lines.append(f"Spec: {spec.model_dump_json(exclude_none=True)}")
    if estimate:
        lines.append(
            f"Estimate: {format_lakhs(estimate.total_inr)} "
            f"({format_lakhs(estimate.range_low_inr)}-{format_lakhs(estimate.range_high_inr)}), "
            f"tier={estimate.tier}, rates={estimate.rates_source}"
        )
    lines.append(f"Reply on WhatsApp: {whatsapp_link(phone, f'Hello {name}, this is Ravikumar.')}")
    return "\n".join(lines)
