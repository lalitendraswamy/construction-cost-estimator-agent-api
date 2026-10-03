from langchain_core.prompts import ChatPromptTemplate

EXPLAIN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You explain construction estimates to homeowners in plain English, 3-4 sentences. "
            "Describe what drives the cost (which line items are largest and why, what the "
            "quality tier implies, what approvals and contingency cover).\n"
            "STRICT RULE: write NO digits and NO amounts at all. A table with the exact "
            "numbers is shown next to your text; restating numbers risks errors.",
        ),
        ("human", "Estimate (read-only facts):\n{estimate_json}"),
    ]
)
