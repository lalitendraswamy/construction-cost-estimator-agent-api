"""Knowledge agent (PRD F5): a prebuilt ReAct agent with one tool, the retriever.

`langchain.agents.create_agent` is the LangChain v1 successor of
`langgraph.prebuilt.create_react_agent`: model <-> ToolNode loop as a compiled graph.
Invoked inside this node, it inherits the parent's checkpointer automatically.
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime

from estimator_agent.agent.context import AgentContext
from estimator_agent.agent.nodes.common import agent_input, recent_dialogue
from estimator_agent.agent.prompts.knowledge import KNOWLEDGE_SYSTEM
from estimator_agent.agent.state import EstimatorState
from estimator_agent.agent.streaming import emit_progress
from estimator_agent.agent.tools.knowledge import make_search_knowledge_base


async def knowledge_node(state: EstimatorState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
    emit_progress("searching_kb")
    ctx = runtime.context
    agent = create_agent(
        ctx.models.chat("small"),
        tools=[make_search_knowledge_base(ctx.retriever)],
        system_prompt=KNOWLEDGE_SYSTEM,
        name="knowledge_agent",
    )
    result = await agent.ainvoke(agent_input(recent_dialogue(state["messages"], 6)))
    messages = result["messages"]
    sources = sorted(
        {s for m in messages if isinstance(m, ToolMessage) and m.artifact for s in m.artifact}
    )
    return {"draft": messages[-1].text, "sources": sources}
