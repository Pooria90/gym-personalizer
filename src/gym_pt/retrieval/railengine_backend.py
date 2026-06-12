"""Legacy Railengine retrieval backend.

Kept as a switchable fallback (``RETRIEVAL_BACKEND=railengine`` in ``.env``).
Requires ``ENGINE_PAT`` / ``ENGINE_ID`` credentials and a populated remote
vector store. Railengine ingestion tooling is not maintained in ``scripts/``;
it will be promoted there if/when the Railengine SDK migration happens.
"""

from __future__ import annotations

from gym_pt.models.exercise import Exercise


class RailengineRetriever:
    """``ExerciseRetriever`` backed by the remote Railengine vector store."""

    async def search(self, query: str, *, max_results: int = 10) -> list[Exercise]:
        # Imported lazily: the rail-engine SDK is an optional extra and the
        # railtracks path must never touch it.
        try:
            from gym_pt.railengine import search_exercises
        except ImportError as e:
            raise RuntimeError(
                "RETRIEVAL_BACKEND=railengine requires the optional rail-engine "
                'SDK — install it with: uv sync --extra railengine'
            ) from e

        return await search_exercises(query, max_results=max_results)
