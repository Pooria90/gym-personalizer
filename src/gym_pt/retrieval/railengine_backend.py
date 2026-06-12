"""Legacy Railengine retrieval backend.

Kept as a switchable fallback (``RETRIEVAL_BACKEND=railengine`` in ``.env``).
Requires ``ENGINE_PAT`` / ``ENGINE_ID`` credentials and a populated remote
vector store (see ``workspace-tmp/ingest.py``).
"""

from __future__ import annotations

from gym_pt.models.exercise import Exercise


class RailengineRetriever:
    """``ExerciseRetriever`` backed by the remote Railengine vector store."""

    async def search(self, query: str, *, max_results: int = 10) -> list[Exercise]:
        # Imported lazily so the railtracks path never touches the rail-engine
        # SDK (which `pyproject.toml` will eventually demote to an extra).
        from gym_pt.railengine import search_exercises

        return await search_exercises(query, max_results=max_results)
