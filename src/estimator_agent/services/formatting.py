"""Deterministic rendering of numbers. The Responder LLM writes prose; the table and the
disclaimer are appended by code so an LLM can never alter a price.

TODO: have a native speaker review the te/hi strings.
"""

from __future__ import annotations

from estimator_agent.domain import Estimate, Language

DISCLAIMERS: dict[Language, str] = {
    Language.EN: "Indicative estimate, final quote after site visit by Sadhguru Associates.",
    Language.TE: "ఇది సూచనాత్మక అంచనా మాత్రమే; సాధ్గురు అసోసియేట్స్ సైట్ సందర్శన తర్వాత తుది కొటేషన్ ఇస్తారు.",
    Language.HI: "यह एक सांकेतिक अनुमान है; अंतिम कोटेशन सद्गुरु एसोसिएट्स द्वारा साइट विज़िट के बाद दिया जाएगा।",
}

UNDER_REVIEW: dict[Language, str] = {
    Language.EN: "Our engineer is reviewing your estimate. We'll share it shortly.",
    Language.TE: "మా ఇంజనీర్ మీ అంచనాను పరిశీలిస్తున్నారు. త్వరలో మీకు తెలియజేస్తాము.",
    Language.HI: "हमारे इंजीनियर आपके अनुमान की समीक्षा कर रहे हैं। जल्द ही साझा करेंगे।",
}

_HEADERS: dict[Language, tuple[str, str, str]] = {
    Language.EN: ("Item", "Amount", "Total"),
    Language.TE: ("అంశం", "మొత్తం", "మొత్తం ఖర్చు"),
    Language.HI: ("मद", "राशि", "कुल"),
}


def format_inr(amount: float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    n = round(amount)
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"


def format_lakhs(amount: float) -> str:
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    return f"₹{amount / 1_00_000:.1f} L"


def estimate_table(estimate: Estimate, language: Language, top_n: int = 5) -> str:
    item_h, amt_h, total_h = _HEADERS[language]
    rows = [f"| {item_h} | {amt_h} |", "|---|---:|"]
    for li in estimate.top_line_items(top_n):
        rows.append(f"| {li.label} | {format_inr(li.amount_inr)} |")
    rows.append(
        f"| Approvals ({estimate.approval_authority}) | {format_inr(estimate.approval_fees_inr)} |"
    )
    rows.append(f"| Contingency | {format_inr(estimate.contingency_inr)} |")
    rows.append(
        f"| **{total_h}** | **{format_lakhs(estimate.total_inr)}** "
        f"({format_lakhs(estimate.range_low_inr)} – {format_lakhs(estimate.range_high_inr)}) |"
    )
    banner = (
        "\n\n_Sample rates — not yet confirmed by Sadhguru Associates._"
        if (estimate.rates_source == "placeholder")
        else ""
    )
    return "\n".join(rows) + banner + f"\n\n_{DISCLAIMERS[language]}_"
