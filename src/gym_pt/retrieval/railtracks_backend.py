"""Railtracks-native retrieval backend (default).

Searches the local Chroma store built by ``scripts/ingest.py`` and maps hits
back to full ``Exercise`` objects through the catalog, so every returned id is
guaranteed to exist in the dataset.
"""

from __future__ import annotations

import logging
from pathlib import Path

from railtracks.retrieval import RetrievalRuntime

from gym_pt.models.exercise import Exercise
from gym_pt.retrieval.catalog import DEFAULT_CATALOG_PATH, load_catalog
from gym_pt.retrieval.runtime import create_runtime

logger = logging.getLogger("gym_pt.retrieval.railtracks")


class RailtracksRetriever:
    """``ExerciseRetriever`` backed by a railtracks ``RetrievalRuntime``."""

    def __init__(self, runtime: RetrievalRuntime, catalog: dict[str, Exercise]):
        self._runtime = runtime
        self._catalog = catalog
        # NOTE: we are good with loading the whole catalog in memory because it's small (~1.5k exercises) for now,
        # but if that ever changes we can switch to a lazy loading approach (e.g. SQLite) without affecting the retrieval logic. 

    @classmethod
    async def create(cls, catalog_path: Path = DEFAULT_CATALOG_PATH) -> RailtracksRetriever:
        return cls(runtime=await create_runtime(), catalog=load_catalog(catalog_path))

    async def search(self, query: str, *, max_results: int = 10) -> list[Exercise]:
        result = await self._runtime.retrieve(query, top_k=max_results)
        out: list[Exercise] = []
        seen: set[str] = set()
        for rc in result.chunks:
            exercise_id = rc.chunk.metadata.get("exercise_id")
            exercise = (
                self._catalog.get(exercise_id) if isinstance(exercise_id, str) else None
            )
            if exercise is None:
                # Stale store entry (dataset changed since last ingest);
                # dropping it preserves the plan-validation invariant.
                logger.warning(
                    "Retrieved chunk has no catalog match (exercise_id=%r); "
                    "re-run scripts/ingest.py",
                    exercise_id,
                )
                continue
            if exercise.id not in seen:
                seen.add(exercise.id)
                out.append(exercise)
        logger.debug("query %r → %d exercise(s)", query, len(out))
        return out
