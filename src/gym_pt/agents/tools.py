import asyncio
import railtracks as rt

from gym_pt.railengine import search_exercises
from gym_pt.models import Exercise, UserProfile, ExerciseQueries
from .agents import Query_Agent


async def retrieve_exercises(query: str, top_k: int = 3) -> list[Exercise] | None:
    """
    Retrieves relevant exercises from the database using semantic search.

    Args:
        query (str): Natural language description of the desired exercises,
                     e.g. 'compound lower body movements for beginners'.
        top_k (int): Maximum number of exercises to return. Defaults to 3.

    Returns:
        list[Exercise]: A list of matching Exercise objects, or None if the search fails.
    """
    try:
        result: list[Exercise] = await search_exercises(query, max_results=top_k)
        # TODO: Add some logs
        return result
    except Exception:
        # TODO: Log the exception
        return None


def _compute_top_k(profile: UserProfile) -> dict[str, int]:
    """
    Distribute a per-plan exercise budget across the five query slots
    proportionally, using the original top_k values as weights.

    Budget:
        total_budget = days_per_week * 8

    This is the same constant used by the pool trimmer in e2e.py, so retrieval
    fetches exactly what the planner will receive. The trim becomes a no-op
    safety net rather than load-bearing logic, and the two mechanisms can't
    drift out of sync.

    Distribution:
        The json_schema_extra["top_k"] values (4, 5, 6, 3, 3 — sum = 21) are
        used as weights. Each slot receives:
            round(weight / 21 * total_budget), floored at 1.

    Example: days_per_week=5 → total_budget=40
        warmup_query    4/21 × 40 ≈  7.6  → 8
        primary_query   5/21 × 40 ≈  9.5  → 10
        secondary_query 6/21 × 40 ≈ 11.4  → 11
        equipment_query 3/21 × 40 ≈  5.7  → 6
        cooldown_query  3/21 × 40 ≈  5.7  → 6

    Example: days_per_week=2 → total_budget=16
        warmup_query    4/21 × 16 ≈  3.0  → 3
        primary_query   5/21 × 16 ≈  3.8  → 4
        secondary_query 6/21 × 16 ≈  4.6  → 5
        equipment_query 3/21 × 16 ≈  2.3  → 2
        cooldown_query  3/21 × 16 ≈  2.3  → 2
    """
    total_budget = profile.days_per_week * 8
    weights = {
        name: meta.json_schema_extra["top_k"]
        for name, meta in ExerciseQueries.model_fields.items()
    }
    weight_sum = sum(weights.values())  # 4 + 5 + 6 + 3 + 3 = 21
    return {
        name: max(1, round(w / weight_sum * total_budget))
        for name, w in weights.items()
    }


async def query_and_retrieve(user_profile: UserProfile) -> list[Exercise]:
    """
    Runs the query builder agent and retrieves exercises in a single step.

    Calls the Query_Agent to generate structured search queries from the user
    profile, then fans out parallel retrieval calls — one per query field —
    and returns a deduplicated list of exercises ordered by query priority.

    Args:
        user_profile (UserProfile): The structured user intake profile containing
                                    goal, fitness level, equipment, and constraints.

    Returns:
        list[Exercise]: Deduplicated exercises across all query dimensions,
                        ordered by query priority (warmup → primary → ... → cooldown).
                        Returns an empty list if all retrieval calls fail.
    """
    output = await rt.call(Query_Agent, str(user_profile))
    queries: ExerciseQueries = output.structured

    top_k_map = _compute_top_k(user_profile)
    coroutines = [
        retrieve_exercises(
            getattr(queries, field_name),
            top_k=top_k_map[field_name],
        )
        for field_name in ExerciseQueries.model_fields
    ]

    results = await asyncio.gather(*coroutines)

    seen: set[str] = set()
    exercises: list[Exercise] = []
    for batch in results:
        # TODO: Debug log; dangerous area
        for ex in batch or []:
            try:
                if ex.id not in seen:
                    seen.add(ex.id)
                    exercises.append(ex)
            except Exception:
                # TODO: Track the error here
                continue

    return exercises


async def swap_exercise(
    exercise: Exercise,
    profile: UserProfile,
    *,
    max_candidates: int = 3,
) -> list[Exercise]:
    """
    Return up to ``max_candidates`` replacements for a single exercise.

    Builds a focused query from the exercise's own category and primary muscles
    combined with the user's equipment and level, so candidates target the same
    muscles and respect the user's constraints — without re-running the full
    intake → retrieve → plan pipeline.

    The Router Agent calls this when the user asks to swap one exercise (e.g.
    "I can't do bench press, give me something else for chest").

    One extra result is fetched so the original exercise can be filtered out
    without the returned list going under budget.

    Args:
        exercise: The exercise to replace.
        profile: The user's current profile, used to constrain by equipment and level.
        max_candidates: Maximum number of replacement options to return (default 3).

    Returns:
        Up to ``max_candidates`` Exercise objects ordered by relevance,
        excluding the original. Returns an empty list if the search fails.
    """
    muscles = " and ".join(exercise.primaryMuscles[:2]) if exercise.primaryMuscles else ""
    equipment_hint = " ".join(profile.equipment[:2]) if profile.equipment else "body only"
    query = (
        f"{exercise.category} {muscles} exercises "
        f"for {profile.level} using {equipment_hint}"
    )

    try:
        results = await search_exercises(query, max_results=max_candidates + 1)
    except Exception:
        return []

    return [ex for ex in results if ex.id != exercise.id][:max_candidates]
