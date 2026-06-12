"""Railtracks RetrievalRuntime factory (Chroma + OpenAI embeddings).

Construct once at startup and reuse — never per request/tool call. Ingest and
retrieve must share the same embedding model on a collection; the model name
comes from settings so call sites can't drift (railtracks raises
``EmbeddingModelMismatchError`` if they do).
"""

from __future__ import annotations

from railtracks.retrieval import RetrievalRuntime, VectorStore
from railtracks.retrieval.chunking import RecursiveCharacterChunker
from railtracks.retrieval.embedding import OpenAIEmbedding
from railtracks.retrieval.stores import ChromaBackend

from gym_pt.config import get_settings

# Longest exercise text in the dataset is ~3.4k chars; this keeps
# one exercise = one chunk, so instructions never detach from name/muscles.
_EXERCISE_CHUNK_SIZE = 6000

_EMBED_BATCH_SIZE = 100


async def create_runtime() -> RetrievalRuntime:
    """Build the runtime against the local Chroma store configured in `.env`."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set in gym/.env — required for the "
            "Railtracks retrieval embedder."
        )

    backend = await ChromaBackend.create(
        collection_name=settings.chroma_collection,
        path=str(settings.chroma_path),
    )
    return RetrievalRuntime(
        chunker=RecursiveCharacterChunker(chunk_size=_EXERCISE_CHUNK_SIZE, overlap=0),
        embedder=OpenAIEmbedding(
            settings.embedding_model,
            api_key=settings.openai_api_key,
        ),
        store=VectorStore(backend),
        batch_size=_EMBED_BATCH_SIZE,
    )
