from __future__ import annotations

from typing import Any, Callable, Literal

from railtown.engine import Railengine

from gym_pt.config import get_settings
from gym_pt.models.exercise import Exercise
from gym_pt.railengine.sdk_patch import apply_railengine_search_patch

VectorStore = Literal["VectorStore1", "VectorStore2", "VectorStore3"]


async def search_exercises(
    query: str,
    *,
    max_results: int = 10,
    pat: str | None = None,
    engine_id: str | None = None,
    vector_store: VectorStore = "VectorStore1",
    model: type[Exercise] = Exercise,
    filter_fn: Callable[[Any], bool] | None = None,
    use_sdk_patch: bool = False,
) -> list[Exercise]:
    """
    Run semantic search and return up to ``max_results`` deserialized exercises.

    On HTTP/request errors inside the SDK search implementation, results may be
    empty (the upstream client logs and yields nothing). Other failures from
    ``Railengine`` propagate to the caller.
    """
    if use_sdk_patch:
        apply_railengine_search_patch()

    settings = get_settings()
    resolved_pat = pat if pat is not None else settings.engine_pat
    resolved_engine = engine_id if engine_id is not None else settings.engine_id

    out: list[Exercise] = []
    async with Railengine(pat=resolved_pat, engine_id=resolved_engine) as client:
        stream = client.search_vector_store(
            engine_id=client.engine_id,
            vector_store=vector_store,
            query=query,
            filter_fn=filter_fn,
            model=model,
        )
        async for item in stream:
            out.append(item)
            if len(out) >= max_results:
                break

    return out


def filter_by_equipment(
    exercises: list[Exercise],
    *needles: str,
) -> list[Exercise]:
    """Keep exercises whose ``equipment`` field contains any substring (case-insensitive)."""
    if not needles:
        return list(exercises)
    lowered = [n.lower() for n in needles if n.strip()]

    def match(ex: Exercise) -> bool:
        eq = ex.equipment.lower()
        return any(n in eq for n in lowered)

    return [ex for ex in exercises if match(ex)]


def filter_by_level(exercises: list[Exercise], level: str) -> list[Exercise]:
    """Keep exercises whose ``level`` equals ``level`` (case-insensitive)."""
    want = level.lower().strip()
    return [ex for ex in exercises if ex.level.lower().strip() == want]
