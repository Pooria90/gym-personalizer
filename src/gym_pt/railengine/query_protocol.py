"""Contracts for turning structured intake into a vector-search query string.

A Railtracks agent may later provide a richer :class:`SearchQueryBuilder`
implementation; :class:`DefaultSearchQueryBuilder` is deterministic (no LLM).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gym_pt.models.plan import UserProfile


@runtime_checkable
class SearchQueryBuilder(Protocol):
    """Builds a natural-language query for ``search_exercises``."""

    def build_query(
        self, profile: UserProfile, *, extra_hints: str | None = None
    ) -> str: ...


class DefaultSearchQueryBuilder:
    """Template-based query text for tests and defaults."""

    def build_query(
        self, profile: UserProfile, *, extra_hints: str | None = None
    ) -> str:
        parts: list[str] = [
            profile.goal,
            f"{profile.days_per_week} days per week",
            profile.level.value,
        ]
        if profile.equipment:
            parts.append("equipment: " + ", ".join(profile.equipment))
        if profile.notes:
            parts.append(profile.notes)
        if extra_hints:
            parts.append(extra_hints)
        return ". ".join(parts)
