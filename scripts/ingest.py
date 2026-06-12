#!/usr/bin/env python3
"""Ingest the free-exercise-db catalog into the local Chroma vector store.

Idempotent: re-runs skip exercises whose content is unchanged (content-hash
upsert), so this is safe to run after dataset updates. Replaces the Railengine
scratch ingester in workspace-tmp/ingest.py as the primary path.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from gym_pt.config import setup_logging
from gym_pt.retrieval import DEFAULT_CATALOG_PATH, ExerciseCatalogLoader, create_runtime

logger = setup_logging(level="INFO")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest exercises into the Railtracks/Chroma vector store"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to the combined exercises.json (default: free-exercise-db/dist)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only ingest the first N exercises (smoke runs)",
    )
    args = parser.parse_args()

    async def run() -> int:
        runtime = await create_runtime()
        loader = ExerciseCatalogLoader(args.data, limit=args.limit)
        stats = await runtime.ingest_all(loader=loader)

        logger.info(
            "Ingest complete: %d loaded, %d embedded, %d skipped (unchanged), %d failed",
            stats.documents_loaded,
            stats.chunks_embedded,
            stats.documents_skipped,
            stats.documents_failed,
        )
        logger.info(
            "Embedding usage: %s tokens, $%.4f",
            stats.total_metrics.input_tokens,
            stats.total_metrics.total_cost or 0.0,
        )

        if stats.documents_failed:
            for failed in stats.failed_documents:
                logger.error("FAILED %s: %s", failed.source, failed.errors)
            return 1
        return 0

    try:
        return asyncio.run(run())
    except Exception as e:
        logger.exception("Ingestion failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
