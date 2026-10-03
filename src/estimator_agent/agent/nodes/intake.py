"""Intake agent (PRD F2): extract fields -> compute missing -> ask, or hand to Estimator.

Routing uses `Command(goto=...)` instead of a conditional edge: the node decides AND
updates state in one return. The `Command[Literal[...]]` annotation tells LangGraph
(and the Mermaid diagram) which nodes are reachable.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import recent_dialogue
from estimator_agent.agent.prompts import LANGUAGE_NAMES
from estimator_agent.agent.prompts.intake import EXTRACT_PROMPT, FIELD_HINTS, QUESTION_PROMPT
from estimator_agent.agent.state import EstimatorState, merge_spec
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.core.llm import structured
from estimator_agent.domain import Extra, Language, ProjectSpec, ProjectType, QualityTier
from estimator_agent.services.units import AreaUnit, to_sqft


class AreaInput(BaseModel):
    value: float = Field(gt=0)
    unit: AreaUnit


class SpecExtraction(BaseModel):
    """What the LLM fills. Areas keep the user's unit; code converts (no LLM arithmetic)."""

    project_type: ProjectType | None = None
    location: str | None = None
    plot_area: AreaInput | None = None
    built_up_area: AreaInput | None = None
    floors: int | None = Field(None, ge=1, le=10)
    tier: QualityTier | None = None
    timeline_months: int | None = None
    budget_ceiling_inr: float | None = None
    extras: list[Extra] = Field(default_factory=list)

    def to_spec_patch(self) -> dict[str, Any]:
        patch = self.model_dump(exclude={"plot_area", "built_up_area"}, exclude_none=True)
        if self.plot_area:
            patch["plot_area_sqft"] = to_sqft(self.plot_area.value, self.plot_area.unit)
        if self.built_up_area:
            patch["built_up_area_sqft"] = to_sqft(self.built_up_area.value, self.built_up_area.unit)
        if not patch.get("extras"):
            patch.pop("extras", None)
        return patch


async def intake_node(
    state: EstimatorState, runtime: Runtime[AgentContext]
) -> Command[Literal["ask_user", "estimator"]]:
    emit_progress("extracting_spec")
    model = runtime.context.models.chat("small")
    current = state.get("spec") or ProjectSpec()
    dialogue = recent_dialogue(state["messages"], 8)

    extraction: SpecExtraction = await (EXTRACT_PROMPT | structured(model, SpecExtraction)).ainvoke(
        {"messages": dialogue, "spec": current.model_dump_json(exclude_none=True)}
    )
    patch = extraction.to_spec_patch()
    missing = merge_spec(current, patch).missing_fields()
    update: dict[str, Any] = {"spec": patch, "missing_fields": missing}

    if not missing:
        return Command(goto="estimator", update=update)

    language = state.get("language", Language.EN)
    question = await (QUESTION_PROMPT | model | StrOutputParser()).ainvoke(
        {
            "messages": dialogue,
            "language_name": LANGUAGE_NAMES[language],
            "missing": "\n".join(f"- {FIELD_HINTS.get(f, f)}" for f in missing[:2]),
        }
    )
    return Command(goto="ask_user", update={**update, "pending_question": question})


def ask_user_node(state: EstimatorState) -> dict[str, Any]:
    """Pause the graph and wait for the user's answer.

    Deliberately tiny: on resume this node re-runs from the top, and `interrupt()` returns
    the resume value instead of pausing. If the LLM question generation lived here, it
    would be re-run (and re-billed) on every resume.
    """
    question = state.get("pending_question") or "Could you share a few more details?"
    answer = interrupt(
        {
            "type": "ask_user",
            "question": question,
            "missing_fields": state.get("missing_fields", []),
        }
    )
    return {
        "messages": [AIMessage(content=question, name="intake"), HumanMessage(content=str(answer))],
        "pending_question": None,
    }
