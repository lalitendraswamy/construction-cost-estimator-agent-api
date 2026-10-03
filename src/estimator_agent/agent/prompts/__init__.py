"""Prompt templates, one module per agent. Prompts are code: version them, review them,
and evaluate changes against the LangSmith dataset before shipping."""

from estimator_agent.domain import Language

LANGUAGE_NAMES: dict[Language, str] = {
    Language.EN: "English",
    Language.TE: "Telugu (use Telugu script)",
    Language.HI: "Hindi (use Devanagari script)",
}

FIRM = "Sadhguru Associates (Ravikumar, Visakhapatnam, Andhra Pradesh)"
