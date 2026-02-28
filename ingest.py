import os
import asyncio
import json
import logging

from glob import glob
from dotenv import load_dotenv
from railtown.engine.ingest import RailengineIngest


def setup_logger(level: int = logging.WARNING) -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(name)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger

logger = setup_logger()


async def main(exercise_files: list[str], max_files: int | None = None):
    async with RailengineIngest(engine_token=engine_token) as client:
        for exercise_file in exercise_files[:max_files]:
            with open(exercise_file, "r") as f:
                exercise = json.load(f)
            logger.info(f"Ingesting exercise: {exercise['name']}...")
            response = await client.upsert(exercise)
            logger.info(f"Status: {response.status_code}\n")


if __name__ == "__main__":
    load_dotenv()

    engine_token = os.getenv("ENGINE_TOKEN")

    data_dir = "free-exercise-db/exercises"
    exercise_files = glob(os.path.join(data_dir, "*.json"))

    logger.info(f"Found {len(exercise_files)} exercise files!")
    asyncio.run(main(exercise_files))
