"""Backend-agnostic retrieval contract for the pipeline.

Everything above this seam (tools, agents, scripts) consumes
``list[Exercise]`` and never imports a concrete backend.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gym_pt.models.exercise import Exercise


@runtime_checkable
class ExerciseRetriever(Protocol):
    """Semantic search over the exercise catalog."""

    async def search(self, query: str, *, max_results: int = 10) -> list[Exercise]: ...
