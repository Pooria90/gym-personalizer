"""Retriever selection and lifecycle.

``get_retriever()`` returns a process-wide singleton per backend, built
lazily on first use. The lock matters: ``query_and_retrieve`` fans out five
concurrent searches, and without it the first call of a run would build five
Chroma runtimes.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from gym_pt.config import get_settings
from gym_pt.retrieval.protocol import ExerciseRetriever

RetrievalBackend = Literal["railtracks", "railengine"]

_retrievers: dict[str, ExerciseRetriever] = {}
_lock = asyncio.Lock()


async def get_retriever(backend: RetrievalBackend | None = None) -> ExerciseRetriever:
    """Return the configured retriever (``RETRIEVAL_BACKEND``, default railtracks).

    Pass ``backend`` to override the setting (used by smoke scripts and
    side-by-side evaluation).
    """
    resolved = backend or get_settings().retrieval_backend
    async with _lock:
        if resolved not in _retrievers:
            if resolved == "railtracks":
                from gym_pt.retrieval.railtracks_backend import RailtracksRetriever

                _retrievers[resolved] = await RailtracksRetriever.create()
            elif resolved == "railengine":
                from gym_pt.retrieval.railengine_backend import RailengineRetriever

                _retrievers[resolved] = RailengineRetriever()
            else:
                raise ValueError(f"Unknown retrieval backend: {resolved!r}")
        return _retrievers[resolved]
