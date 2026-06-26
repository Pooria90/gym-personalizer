"""CLI wrapper around the plan-generation pipeline.

Thin by design: the orchestration lives in gym_pt.service.pipeline; this script
only runs it and renders the result to a standalone HTML workout card.
"""

import asyncio
import logging
from pathlib import Path

from gym_pt.service import PlanResult, generate_plan
from gym_pt.utils import (
    enrich_workout_plan_with_instructions,
    render_workout_plan_html,
)

logger = logging.getLogger("gym_pt.e2e")


def write_workout_plan_html(result: PlanResult, path: Path) -> None:
    """Enrich plan with catalog instructions and write a standalone HTML file."""
    enriched = enrich_workout_plan_with_instructions(
        result.plan.model_dump(), result.exercises
    )
    path.write_text(render_workout_plan_html(enriched), encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
    )

    user_query = """
        Give beginner plan for 4 days per week, for strength training,
        machine and dumbbells, and cables for the equipment.
    """
    result = asyncio.run(generate_plan(user_query))

    metadata_dir = Path(__file__).resolve().parent.parent / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    out_html = metadata_dir / "e2e_plan.html"
    write_workout_plan_html(result, out_html)
    logger.info("Wrote workout plan HTML to %s", out_html)
