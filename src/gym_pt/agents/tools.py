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
    Scale each query's base top_k by a multiplier derived from the user profile.

    Two factors drive the multiplier:
    - day_scale   = days_per_week / 3   (3-day plan is the baseline → 1.0)
    - eq_scale    = max(1, len(equipment)) / 2  (2-item list is the baseline → 1.0;
                    bodyweight-only counts as 1 to avoid a zero denominator)

    multiplier = max(1.0, (day_scale + eq_scale) / 2)

    The average of the two factors is taken so neither dominates. The floor of 1.0
    ensures the pool never shrinks below the base values — a very short or
    equipment-light plan gets the defaults, not less.

    Example: days_per_week=5, equipment=['barbell','dumbbell','cable','machine']
        day_scale  = 5/3  ≈ 1.67
        eq_scale   = 4/2  = 2.00
        multiplier = (1.67 + 2.00) / 2 ≈ 1.83
        primary_query base=5 → round(5 × 1.83) = 9

    Each computed value is also floored at 1 so no query ever requests 0 results.
    """
    day_scale = profile.days_per_week / 3
    eq_scale = max(1, len(profile.equipment)) / 2
    multiplier = max(1.0, (day_scale + eq_scale) / 2)
    return {
        field_name: max(1, round(meta.json_schema_extra["top_k"] * multiplier))
        for field_name, meta in ExerciseQueries.model_fields.items()
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
