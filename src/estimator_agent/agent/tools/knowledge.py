"""search_knowledge_base: the retriever exposed as a tool (RAG inside a ReAct agent)."""

from __future__ import annotations

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field


class SearchKBInput(BaseModel):
    query: str = Field(description="Self-contained English search query")


def make_search_knowledge_base(retriever: BaseRetriever | None) -> BaseTool:
    # content_and_artifact: the model sees `content`; code gets `artifact` (source list)
    # on the ToolMessage without spending tokens on it.
    @tool(
        "search_knowledge_base", args_schema=SearchKBInput, response_format="content_and_artifact"
    )
    async def search_knowledge_base(query: str) -> tuple[str, list[str]]:
        """Search Sadhguru Associates' documents: approvals (GVMC/VUDA), materials, quality
        tiers, payment stages, timelines, Vaastu basics and services."""
        if retriever is None:
            return "The knowledge base is not configured yet.", []
        docs = await retriever.ainvoke(query)
        if not docs:
            return "No relevant documents found.", []
        content = "\n\n".join(
            f"[source_doc={d.metadata.get('source_doc')} section={d.metadata.get('section', '')}]\n"
            f"{d.page_content}"
            for d in docs
        )
        sources = sorted({str(d.metadata.get("source_doc")) for d in docs})
        return content, sources

    return search_knowledge_base
