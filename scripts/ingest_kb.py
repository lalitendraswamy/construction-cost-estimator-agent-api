"""Embed data/knowledge_base/*.md into Atlas Vector Search. `python -m scripts.ingest_kb`"""

from __future__ import annotations

from pathlib import Path

from estimator_agent.core.config import export_provider_env, get_settings
from estimator_agent.core.llm import LangChainModelRegistry
from estimator_agent.rag.ingest import ingest_folder
from estimator_agent.rag.vectorstore import build_vector_store

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"


def main() -> None:
    settings = get_settings()
    export_provider_env(settings)
    store = build_vector_store(settings, LangChainModelRegistry(settings).embeddings())
    n = ingest_folder(KB_DIR, store)
    print(f"ingested {n} chunks from {KB_DIR}")


if __name__ == "__main__":
    main()
