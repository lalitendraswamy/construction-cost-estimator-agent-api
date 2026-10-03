"""Contact agent (PRD F6): ReAct agent that collects name/phone/channel/slot and calls
side-effect tools, each of which pauses for the user's "yes" via interrupt()."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain.agents import create_agent
from langgraph.runtime import Runtime

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import agent_input, current_thread_id, recent_dialogue
from estimator_agent.agent.prompts.contact import CONTACT_SYSTEM
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.agent.tools.contact import IST, build_contact_tools
from estimator_agent.domain import Language


async def contact_node(state: EstimatorState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    emit_progress("contacting")
    ctx = runtime.context
    thread_id = current_thread_id()
    lead = state.get("lead")
    tools = build_contact_tools(
        ctx,
        thread_id=thread_id,
        language=state.get("language", Language.EN),
        spec=state.get("spec"),
        estimate=state.get("estimate"),
    )
    agent = create_agent(
        ctx.models.chat("small"),
        tools=tools,
        system_prompt=CONTACT_SYSTEM.format(
            owner_name=ctx.settings.owner_name,
            today=datetime.now(IST).strftime("%A %d %B %Y"),
            lead=lead.model_dump_json(exclude_none=True) if lead else "{}",
        ),
        name="contact_agent",
    )
    result = await agent.ainvoke(agent_input(recent_dialogue(state["messages"], 10)))
    update: dict[str, Any] = {"draft": result["messages"][-1].text}
    if saved := await ctx.leads.get_by_thread(thread_id):
        update["lead"] = saved
    return update
