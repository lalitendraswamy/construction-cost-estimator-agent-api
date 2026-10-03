"""Knowledge-base ingest: load Markdown -> split by headers -> split by size -> embed -> store.

Each chunk keeps `source_doc` and `section` metadata so the Knowledge agent can cite it.
English originals are stored; the Responder translates answers into the user's language.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from estimator_agent.core.logging import get_logger

log = get_logger(__name__)

_HEADER_SPLITTER = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "title"), ("##", "section")], strip_headers=False
)
_SIZE_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def load_markdown_docs(folder: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(folder.glob("*.md")):
        for part in _HEADER_SPLITTER.split_text(path.read_text(encoding="utf-8")):
            part.metadata.update({"source_doc": path.stem, "language": "en"})
            docs.append(part)
    return docs


def chunk(docs: list[Document]) -> list[Document]:
    return _SIZE_SPLITTER.split_documents(docs)


def ingest_folder(folder: Path, store: VectorStore, *, replace: bool = True) -> int:
    chunks = chunk(load_markdown_docs(folder))
    if replace and hasattr(store, "collection"):
        store.collection.delete_many({})  # simple full refresh; TODO: incremental by hash
    # Deterministic ids make re-ingest idempotent.
    ids = [f"{c.metadata['source_doc']}:{i}" for i, c in enumerate(chunks)]
    store.add_documents(chunks, ids=ids)
    log.info("kb_ingested", chunks=len(chunks), folder=str(folder))
    return len(chunks)
