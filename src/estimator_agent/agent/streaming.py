"""Progress events emitted from inside nodes (stream_mode="custom")."""

from __future__ import annotations

from langgraph.config import get_stream_writer

PROGRESS_LABELS: dict[str, str] = {
    "detecting_language": "Understanding your message…",
    "routing": "Thinking…",
    "extracting_spec": "Noting your project details…",
    "computing_quantities": "Calculating material quantities…",
    "fetching_rates": "Calculating rates…",
    "pricing": "Pricing line items…",
    "validating": "Double-checking the numbers…",
    "explaining": "Preparing your estimate…",
    "searching_kb": "Looking that up…",
    "contacting": "Arranging contact…",
    "awaiting_owner": "Our engineer is reviewing your estimate…",
}


def emit_progress(stage: str) -> None:
    """Safe to call outside a streaming run (writer is a no-op then)."""
    try:
        writer = get_stream_writer()
    except RuntimeError:  # called outside a graph run, e.g. a unit test
        return
    writer({"type": "progress", "stage": stage, "label": PROGRESS_LABELS.get(stage, stage)})
