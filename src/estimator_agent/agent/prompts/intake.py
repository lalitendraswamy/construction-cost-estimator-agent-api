from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from estimator_agent.agent.prompts import FIRM

EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extract construction project details from the conversation. Use ONLY what the "
            "user explicitly said; leave a field null if unknown. Never guess.\n"
            "- floors: total floors including ground. 'G' = 1, 'G+1' = 2, 'G+2' = 3.\n"
            "- areas: copy the number and the unit the user used (sqyd for 'gajalu' / "
            "'square yards', sqft, sqm, cent, acre). Do not convert.\n"
            "- If the user changes a value, return the NEW value.\n"
            "Already known (do not repeat unless changed): {spec}",
        ),
        MessagesPlaceholder("messages"),
    ]
)

FIELD_HINTS = {
    "project_type": "what they are building (new house, commercial, renovation, interior, "
    "compound wall)",
    "location": "the area / locality and city",
    "plot_area": "plot size (square yards or square feet)",
    "floors": "number of floors (G, G+1, G+2…)",
    "tier": "quality tier: Basic (economical materials), Standard (branded mid-range), "
    "Premium (high-end finishes)",
}

QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"You are the friendly estimator assistant of {FIRM}. Ask the user for the "
            "missing details below: at most TWO in one short message. If asking about the "
            "quality tier, briefly explain the three tiers. No prices. "
            "Write in {language_name}.\n\nMissing:\n{missing}",
        ),
        MessagesPlaceholder("messages"),
    ]
)
