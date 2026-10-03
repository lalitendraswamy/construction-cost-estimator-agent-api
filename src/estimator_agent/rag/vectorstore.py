"""MongoDB Atlas Vector Search store over the `kb_chunks` collection.

langchain-mongodb uses the *sync* PyMongo driver; its async methods run in a thread
pool. That is fine at this scale; keep it separate from the app's AsyncMongoClient.
"""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient

from estimator_agent.core.config import Settings
from estimator_agent.db import mongo


def build_vector_store(
    settings: Settings, embeddings: Embeddings, client: MongoClient[dict[str, Any]] | None = None
) -> MongoDBAtlasVectorSearch:
    client = client or MongoClient(mongo.require_uri(settings), appname=f"{settings.app_name}-rag")
    collection = client[settings.mongodb_db][mongo.KB_CHUNKS]
    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name=settings.vector_index_name,
        text_key="text",
        embedding_key="embedding",
        relevance_score_fn="cosine",
    )


def build_retriever(store: MongoDBAtlasVectorSearch, k: int = 4) -> VectorStoreRetriever:
    # TODO(learn): try search_type="mmr" for diversity, or a pre_filter on language/source_doc.
    return store.as_retriever(search_kwargs={"k": k})
