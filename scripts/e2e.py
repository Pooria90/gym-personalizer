"""CLI wrapper around the plan-generation pipeline.

Thin by design: orchestration lives in gym_pt.service. This script creates a
persisted session (intake → plan, saved to the JSON state snapshot, with a
memory event recorded) and renders the result to a standalone HTML workout card.
"""

import asyncio
import logging
from pathlib import Path

from gym_pt.config import get_settings
from gym_pt.service import (
    JsonSnapshot,
    Session,
    SnapshotMemory,
    SnapshotSessionStore,
    create_session,
)
from gym_pt.utils import (
    enrich_workout_plan_with_instructions,
    render_workout_plan_html,
)

logger = logging.getLogger("gym_pt.e2e")


def write_workout_plan_html(session: Session, path: Path) -> None:
    """Enrich plan with catalog instructions and write a standalone HTML file."""
    enriched = enrich_workout_plan_with_instructions(
        session.plan.model_dump(), session.exercises
    )
    path.write_text(render_workout_plan_html(enriched), encoding="utf-8")


async def main(user_query: str) -> Session:
    settings = get_settings()
    store = SnapshotSessionStore(JsonSnapshot(settings.state_path / "sessions.json"))
    memory = SnapshotMemory(JsonSnapshot(settings.state_path / "memory.json"))
    return await create_session(user_query, store=store, memory=memory)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
    )

    user_query = """
        Give beginner plan for 4 days per week, for strength training,
        machine and dumbbells, and cables for the equipment.
    """
    session = asyncio.run(main(user_query))

    repo_root = Path(__file__).resolve().parent.parent
    metadata_dir = repo_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    out_html = metadata_dir / "e2e_plan.html"
    write_workout_plan_html(session, out_html)

    logger.info("Session %s persisted to %s", session.id, get_settings().state_path)
    logger.info("Wrote workout plan HTML to %s", out_html)
