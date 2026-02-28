import os
import asyncio
import logging

from pydantic import BaseModel
from devtools import pprint
from dotenv import load_dotenv
from railtown.engine import Railengine


def setup_logger(name: str = __name__, level: int = logging.WARNING) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(name)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger

logger = setup_logger(level=logging.INFO)


class ExerciseModel(BaseModel):
    name: str
    force: str
    level: str
    mechanic: str
    equipment: str
    primaryMuscles: list[str]
    secondaryMuscles: list[str]
    instructions: list[str]
    category: str
    images: list[str]
    id: str


async def main(
        query: str | None = None, 
        pat=None, 
        engine_id=None,
        max_results: int = 5
    ) -> int:
    # Initialize client (reads from ENGINE_PAT env var)
    async with Railengine(pat=pat, engine_id=engine_id) as client:
        ## Search vector store
        results = client.search_vector_store(
            engine_id=client.engine_id,
            query=query or "",
            model=ExerciseModel
        )
        logger.info("Semantic Search COMPLETE")

        count = 0
        async for item in results:
            logger.info(f"Item {count + 1}...")
            pprint(item)
            count += 1
            if count >= max_results:
                break
    return count


if __name__ == "__main__":
    load_dotenv()
    pat = os.getenv("ENGINE_PAT")
    engine_id = os.getenv("ENGINE_ID")

    query = "exercises with cables that target the biceps for strength training"

    res = asyncio.run(main(query, pat, engine_id, max_results=5))
    logger.info(f"Found {res} results")