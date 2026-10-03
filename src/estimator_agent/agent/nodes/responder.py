"""Responder: the only node that talks to the user. Writes prose in the user's language
(LCEL: prompt | model | parser), then code appends the price table + disclaimer."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.runtime import Runtime

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import recent_dialogue
from estimator_agent.agent.prompts import LANGUAGE_NAMES
from estimator_agent.agent.prompts.responder import RESPONDER_PROMPT
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.tools.language import text_to_speech
from estimator_agent.domain import InputMode, Intent, Language
from estimator_agent.services.formatting import estimate_table, format_lakhs

_ESTIMATE_INTENTS = {Intent.ESTIMATE, Intent.MODIFY}


def build_facts(state: EstimatorState) -> str:
    """Everything the Responder may say, pre-computed by code."""
    facts: list[str] = []
    intent = state.get("intent")
    estimate = state.get("estimate")
    if intent in _ESTIMATE_INTENTS and estimate is not None:
        facts.append(
            f"Estimate: {estimate.tier} tier, {estimate.city}, built-up "
            f"{estimate.built_up_area_sqft:.0f} sqft. Total {format_lakhs(estimate.total_inr)} "
            f"(range {format_lakhs(estimate.range_low_inr)} to {format_lakhs(estimate.range_high_inr)})."
        )
        if estimate.summary:
            facts.append(f"Explanation: {estimate.summary}")
        if estimate.validation_flag:
            facts.append("Note: rates need manual review by the engineer; say so gently.")
        if variants := state.get("variants"):
            prev = variants[-1]
            diff = estimate.total_inr - prev.total_inr
            facts.append(
                f"Previous estimate: {prev.tier} tier, {format_lakhs(prev.total_inr)}. "
                f"Difference: {'+' if diff >= 0 else '-'}{format_lakhs(abs(diff))}."
            )
        if state.get("approval") in {"approved", "edited"}:
            facts.append("This estimate was reviewed by our engineer.")
    if draft := state.get("draft"):
        facts.append(f"Specialist answer (translate faithfully): {draft}")
    if sources := state.get("sources"):
        facts.append(f"Sources: {', '.join(sources)}")
    if intent == Intent.CHIT_CHAT:
        facts.append("Offer to estimate the user's construction cost.")
    return "\n".join(facts) or "(none)"


async def responder_node(state: EstimatorState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    language = state.get("language", Language.EN)
    intent = state.get("intent", Intent.CHIT_CHAT)
    chain = RESPONDER_PROMPT | runtime.context.models.chat("small") | StrOutputParser()
    text: str = await chain.ainvoke(
        {
            "language_name": LANGUAGE_NAMES[language],
            "intent": intent.value,
            "facts": build_facts(state),
            "messages": recent_dialogue(state["messages"], 6),
        }
    )
    estimate = state.get("estimate")
    if intent in _ESTIMATE_INTENTS and estimate is not None:
        text = f"{text}\n\n{estimate_table(estimate, language)}"

    audio_url = None
    if state.get("input_mode") == InputMode.VOICE:
        audio_url = await text_to_speech.ainvoke({"text": text, "language": language})

    return {"messages": [AIMessage(content=text, name="responder")], "audio_url": audio_url}
