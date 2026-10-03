from __future__ import annotations

from pathlib import Path

from estimator_agent.rag.ingest import chunk, load_markdown_docs

KB = Path(__file__).resolve().parents[2] / "data" / "knowledge_base"


def test_kb_chunks_carry_citation_metadata() -> None:
    chunks = chunk(load_markdown_docs(KB))
    assert len(chunks) >= 6
    assert all(c.metadata.get("source_doc") for c in chunks)
    approvals = [c for c in chunks if c.metadata["source_doc"] == "approvals_guide"]
    assert any("VUDA" in c.page_content for c in approvals)
    assert all(len(c.page_content) <= 800 for c in chunks)
