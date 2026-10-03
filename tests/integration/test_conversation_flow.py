"""PRD §6 walkthrough as an executable test: the real compiled graph, real checkpointer,
real deterministic tools; only the LLM is scripted. If this passes, the graph wiring,
interrupts, resume, subgraph boundaries and reducers all work."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from estimator_agent.agent.runner import ChatRunner, TurnEvent
from estimator_agent.domain import ApprovalStatus, Language, QualityTier, RateCard
from estimator_agent.services.formatting import DISCLAIMERS, UNDER_REVIEW
from tests.fakes import FakeRetriever, ScriptedChatModel, make_context, make_runner

pytestmark = pytest.mark.integration


async def turn(runner: ChatRunner, thread: str, text: str) -> list[TurnEvent]:
    return [ev async for ev in runner.stream_message(thread, text)]


def last(events: list[TurnEvent]) -> TurnEvent:
    return events[-1]


def route(intent: str) -> dict[str, Any]:
    return {"intent": intent, "reason": "test"}


async def test_prd_walkthrough_turns_1_to_5(model: ScriptedChatModel, runner: ChatRunner) -> None:
    model.structured_outputs = {
        "LanguageGuess": [{"language": "te", "confident": True}] * 2,
        "RouteDecision": [route("estimate"), route("modify")],
        "SpecExtraction": [
            {"project_type": "new_house"},
            {"location": "Madhurawada", "plot_area": {"value": 200, "unit": "sqyd"}},
            {"floors": 2, "tier": "standard"},
            {"tier": "premium"},
        ],
    }
    thread = "thread-walkthrough"

    # Turn 1: intent=estimate, spec empty -> Intake asks -> graph pauses at ask_user
    ev = last(await turn(runner, thread, "Naku illu kattali, entha avutundi?"))
    assert ev.event == "interrupt"
    assert ev.data["type"] == "ask_user"
    assert ev.data["language"] == Language.TE
    assert "location" in ev.data["missing_fields"]

    # Turn 2: answer resumes the SAME run; sq yd converted to sq ft by code
    ev = last(await turn(runner, thread, "Madhurawada, 200 sq yards"))
    assert ev.event == "interrupt"
    assert set(ev.data["missing_fields"]) == {"floors", "tier"}
    view = await runner.thread_view(thread)
    assert view["spec"].plot_area_sqft == 1800

    # Turn 3: spec complete -> estimator subgraph -> responder
    events = await turn(runner, thread, "G+1, standard")
    ev = last(events)
    assert ev.event == "final"
    est = ev.data["estimate"]
    # A = 1800 * 0.6 * 2 = 2160 sqft; 2160*2600 + GVMC(45*2160+15000) = 5,728,200; +7% => 6,129,174
    assert est.built_up_area_sqft == 2160
    assert est.approval_authority == "GVMC"
    assert est.total_inr == 6_129_000
    assert est.range_low_inr < est.total_inr < est.range_high_inr
    assert DISCLAIMERS[Language.TE] in ev.data["reply"]
    assert any(e.event == "progress" and e.data["stage"] == "fetching_rates" for e in events)

    # Turn 5 ("Premium lo entha?"): what-if keeps the rest of the spec, archives old estimate
    ev = last(await turn(runner, thread, "Premium lo entha?"))
    assert ev.event == "final"
    assert ev.data["estimate"].tier == QualityTier.PREMIUM
    view = await runner.thread_view(thread)
    assert [v.tier for v in view["variants"]] == [QualityTier.STANDARD]
    assert view["spec"].location == "Madhurawada"  # merge reducer kept it


async def test_estimate_over_one_crore_waits_for_owner(model: ScriptedChatModel) -> None:
    context = make_context(model)
    runner = make_runner(context)
    model.structured_outputs = {
        "LanguageGuess": [{"language": "en", "confident": True}] * 2,
        "RouteDecision": [route("estimate")],
        "SpecExtraction": [
            {
                "project_type": "commercial",
                "location": "Madhurawada",
                "built_up_area": {"value": 30000, "unit": "sqft"},
                "tier": "premium",
            }
        ],
    }
    thread = "thread-big-one"

    ev = last(await turn(runner, thread, "Quote for a 30000 sqft premium commercial building"))
    assert ev.event == "interrupt"
    assert ev.data["type"] == "owner_approval"
    assert "estimate" not in ev.data  # unapproved numbers never reach the user
    assert len(context.notifier.sent) == 1  # type: ignore[attr-defined]

    # User pings while waiting: graph is NOT resumed
    ev = last(await turn(runner, thread, "any update please?"))
    assert ev.data["reply"] == UNDER_REVIEW[Language.EN]

    view = await runner.resume_owner_approval(thread, {"action": "edit", "total_inr": 10_00_00_000})
    assert view["approval"] == ApprovalStatus.EDITED
    assert view["estimate"].total_inr == 10_00_00_000
    assert view["pending"] is None
    assert (
        len(context.notifier.sent) == 1
    )  # resume did not re-send (side effect outside interrupt node)


async def test_validator_retries_with_default_city_rates(model: ScriptedChatModel) -> None:
    context = make_context(model)
    # A bad rate card for Vijayawada (rate far outside the band) must not reach the user.
    await context.rates.upsert(
        RateCard(
            city="vijayawada",
            tier=QualityTier.STANDARD,
            base_rate_per_sqft=9000,
            band_min_per_sqft=2200,
            band_max_per_sqft=3100,
            shares={"labour": 0.5, "finishing": 0.5},
            source="typo",
        )
    )
    runner = make_runner(context)
    model.structured_outputs = {
        "LanguageGuess": [{"language": "en", "confident": True}],
        "RouteDecision": [route("estimate")],
        "SpecExtraction": [
            {
                "project_type": "new_house",
                "location": "Benz Circle, Vijayawada",
                "built_up_area": {"value": 2000, "unit": "sqft"},
                "tier": "standard",
            }
        ],
    }
    ev = last(
        await turn(runner, "thread-validate", "Estimate 2000 sqft standard house in Vijayawada")
    )
    est = ev.data["estimate"]
    assert est.city == "visakhapatnam"  # retried with the default card
    assert est.validation_flag is None


async def test_knowledge_question_cites_source(model: ScriptedChatModel) -> None:
    retriever = FakeRetriever(
        docs=[Document("VUDA approves layouts...", metadata={"source_doc": "approvals_guide"})]
    )
    runner = make_runner(make_context(model, retriever=retriever))
    model.structured_outputs = {
        "LanguageGuess": [{"language": "en", "confident": True}],
        "RouteDecision": [route("question")],
    }
    model.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "search_knowledge_base", "args": {"query": "VUDA approval"}, "id": "c1"}
            ],
        ),
        "VUDA approval is ... Source: approvals_guide",
        "Here is what VUDA approval means.",
    ]
    ev = last(await turn(runner, "thread-kb", "What is VUDA approval exactly?"))
    assert ev.event == "final"
    assert ev.data["sources"] == ["approvals_guide"]


async def test_contact_tool_waits_for_confirmation(model: ScriptedChatModel) -> None:
    context = make_context(model)
    runner = make_runner(context)
    model.structured_outputs = {
        "LanguageGuess": [{"language": "en", "confident": True}],
        "RouteDecision": [route("contact")],
    }
    model.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "notify_owner",
                    "args": {"name": "Ravi", "phone": "98765 43210", "channel": "whatsapp"},
                    "id": "c1",
                }
            ],
        ),
        "Done, Ravikumar will WhatsApp you.",
        "Ravikumar will contact you on WhatsApp shortly.",
    ]
    thread = "thread-contact"
    ev = last(
        await turn(runner, thread, "I want to talk to Ravikumar, I'm Ravi 9876543210 WhatsApp")
    )
    assert ev.event == "interrupt"
    assert ev.data["type"] == "confirm_action"
    assert ev.data["action"] == "notify_owner"
    assert context.notifier.sent == []  # nothing sent before "yes"  # type: ignore[attr-defined]

    ev = last(await turn(runner, thread, "yes"))
    assert ev.event == "final"
    assert len(context.notifier.sent) == 1  # type: ignore[attr-defined]
    view = await runner.thread_view(thread)
    assert view["lead"].owner_notified is True
    assert view["lead"].phone == "919876543210"
