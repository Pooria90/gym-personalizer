#!/usr/bin/env python3
"""Manual smoke test: semantic exercise search through the retriever seam.

Defaults to the backend configured via RETRIEVAL_BACKEND in gym/.env
(railtracks unless overridden); pass --backend to force one explicitly.
The railengine backend needs real ENGINE_PAT / ENGINE_ID credentials;
the railtracks backend needs a populated local store (scripts/ingest.py).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from devtools import pprint

from gym_pt.config import setup_logging
from gym_pt.retrieval import get_retriever

logger = setup_logging(level="INFO")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test exercise retrieval")
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
    parser.add_argument(
        "-b",
        "--backend",
        choices=["railtracks", "railengine"],
        default=None,
        help="Retrieval backend (default: RETRIEVAL_BACKEND setting)",
    )
    args = parser.parse_args()

    async def run() -> None:
        retriever = await get_retriever(args.backend)
        results = await retriever.search(args.query, max_results=args.max_results)
        logger.info("Got %s result(s) from %s", len(results), type(retriever).__name__)
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
