#!/usr/bin/env python3
"""Manual smoke test: vector search against real Railengine credentials in gym/.env."""

from __future__ import annotations

import argparse
import asyncio
import sys

from devtools import pprint

from gym_pt.config import setup_logging
from gym_pt.railengine import search_exercises

logger = setup_logging(level="INFO")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test gym_pt search_exercises")
    parser.add_argument(
        "query",
        nargs="?",
        default="exercises for biceps with cables",
        help="Natural-language search query",
    )
    parser.add_argument(
        "-n",
        "--max-results",
        type=int,
        default=5,
        help="Max exercises to print",
    )
    args = parser.parse_args()

    async def run() -> None:
        results = await search_exercises(args.query, max_results=args.max_results, use_sdk_patch=False)
        logger.info("Got %s result(s)", len(results))
        for i, item in enumerate(results, 1):
            logger.info("--- Item %s ---", i)
            pprint(item)

    try:
        asyncio.run(run())
    except Exception as e:
        logger.exception("Smoke retrieval failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
