import logging
from pathlib import Path
from typing import Any, Mapping, cast

import railtracks as rt
from rich import print

from gym_pt.agents import *
from gym_pt.models import *
from gym_pt.utils import *


# Logging stuff
_logging_level = logging.DEBUG

def set_logger(level = _logging_level):
    logger = logging.getLogger("E2E")
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = set_logger()


def validate_plan_exercise_ids(plan: Mapping[str, Any], exercises: list) -> None:
    """Ensure every ``exercise_id`` on the plan appears in retrieved exercises (by catalog ``id``)."""
    allowed: set[str] = set()
    for ex in exercises:
        if isinstance(ex, Mapping):
            eid = ex.get("id")
        else:
            eid = getattr(ex, "id", None)
        if eid is not None:
            allowed.add(str(eid))
    bad: set[str] = set()
    used_ids: set[str] = set()
    n_planned = 0
    for day in plan.get("days") or []:
        if not isinstance(day, Mapping):
            continue
        for ex in day.get("exercises") or []:
            if not isinstance(ex, Mapping):
                continue
            n_planned += 1
            eid = ex.get("exercise_id")
            if eid is None or str(eid) == "":
                bad.add("(missing exercise_id)")
            else:
                sid = str(eid)
                used_ids.add(sid)
                if sid not in allowed:
                    bad.add(sid)
    if bad:
        logger.debug(
            "Plan id validation failed: %d planned exercise slot(s), "
            "unknown or missing id(s): %s",
            n_planned,
            sorted(bad),
        )
        raise ValueError(
            "Plan references exercise_id(s) not in retrieved set: "
            + ", ".join(sorted(bad))
        )
    logger.debug(
        "Plan id validation passed: %d planned exercise(s), %d unique id(s), "
        "all present in retrieved catalog (%d exercise(s))",
        n_planned,
        len(used_ids),
        len(allowed),
    )


# Main entry point & flow
@rt.function_node
async def main(user_query: str):
    # 1. Intake the userprofile using the query
    intake_output = await rt.call(Intake_Agent, user_query)
    profile = intake_output.structured
    logger.debug(profile)

    # 2. Retrieve Exercises
    exercises = cast(
        list,
        await rt.call(
            rt.function_node(query_and_retrieve),
            profile,
        ),
    )
    logger.debug("Retrieved %d exercises", len(exercises))

    # 3. Planning
    fields_to_keep = [
        "id",
        "equipment",
        "primaryMuscles",
        "secondaryMuscles",
        "category",
    ]
    filtered_exercises = [
        {k: ex.__getattribute__(k) for k in fields_to_keep} for ex in exercises
    ]


    plan_query = {"profile": profile, "exercises": filtered_exercises}
    plan_output = await rt.call(
        Planner_Agent,
        str(plan_query)
    )
    plan_struct = plan_output.structured
    validate_plan_exercise_ids(plan_struct.model_dump(), exercises)

    final_output = {
        "profile": profile,
        "exercises": exercises,
        "plan": plan_struct,
    }

    return final_output



flow = rt.Flow("End-to-End", entry_point=main)


def write_workout_plan_html(result: dict, path: Path) -> None:
    """Enrich plan with catalog instructions and write a standalone HTML file."""
    plan = result["plan"]
    plan_dict = plan.model_dump() if hasattr(plan, "model_dump") else dict(plan)
    enriched = enrich_workout_plan_with_instructions(plan_dict, result["exercises"])
    path.write_text(render_workout_plan_html(enriched), encoding="utf-8")


# Run forest, run!
if __name__ == "__main__":
    user_query = """
        Give intermediate plan for 3 days per week, for strength training,
        machine and dumbbells for the equipment.
    """
    result = flow.invoke(user_query)
    # print(result)

    repo_root = Path(__file__).resolve().parent.parent
    metadata_dir = repo_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    out_html = metadata_dir / "e2e_plan.html"
    write_workout_plan_html(result, out_html)
    logger.info("Wrote workout plan HTML to %s", out_html)