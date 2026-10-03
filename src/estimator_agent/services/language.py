"""Cheap, deterministic language detection by Unicode script.

Telugu and Devanagari scripts are unambiguous, so we don't pay for an LLM call.
Latin text ("Naku illu kattali" is romanised Telugu!) returns None, and the
Input node falls back to a small LLM classifier.
"""

from __future__ import annotations

from estimator_agent.domain import Language

_TELUGU = range(0x0C00, 0x0C80)
_DEVANAGARI = range(0x0900, 0x0980)


def detect_script_language(text: str, threshold: float = 0.3) -> Language | None:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    te = sum(1 for c in letters if ord(c) in _TELUGU)
    hi = sum(1 for c in letters if ord(c) in _DEVANAGARI)
    if te / len(letters) >= threshold:
        return Language.TE
    if hi / len(letters) >= threshold:
        return Language.HI
    return None
