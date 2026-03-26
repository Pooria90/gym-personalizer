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

    fields = ExerciseQueries.model_fields
    coroutines = [
        retrieve_exercises(
            getattr(queries, field_name),
            top_k=meta.json_schema_extra["top_k"],
        )
        for field_name, meta in fields.items()
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
