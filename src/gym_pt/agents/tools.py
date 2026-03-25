import railtracks as rt

from gym_pt.railengine import search_exercises
from gym_pt.models import Exercise

@rt.function_node
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
    except Exception as e:
        # TODO: Log the exception
        return None



        
