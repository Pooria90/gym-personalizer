"""Plan-generation pipeline, extracted from scripts/e2e.py.

The single importable orchestration path (intake → retrieve → trim → plan →
validate) shared by the CLI and the API. HTML rendering stays a
caller/presentation concern and lives outside this module.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, cast
from uuid import uuid4

import railtracks as rt
from pydantic import BaseModel

from gym_pt.agents import Intake_Agent, Planner_Agent, query_and_retrieve
from gym_pt.models import Exercise, UserProfile, WorkoutPlan

logger = logging.getLogger("gym_pt.service.pipeline")

# Pool sizing: ~8 candidate exercises per planned day keeps the planner prompt
# focused. Matches the retrieval budget in agents/tools._compute_top_k, so the
# trim is a safety net rather than load-bearing.
_POOL_PER_DAY = 8

# Only these fields are handed to the planner — enough to reason about and
# reference exercises by id without flooding the prompt with instructions/images.
_PLANNER_FIELDS = ("id", "equipment", "primaryMuscles", "secondaryMuscles", "category")


class PlanResult(BaseModel):
    """Typed result of a full pipeline run."""

    profile: UserProfile
    exercises: list[Exercise]  # the trimmed retrieved pool the plan was built from
    plan: WorkoutPlan


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


def _assign_slot_ids(plan: WorkoutPlan) -> None:
    """Stamp a fresh ``slot_id`` on every planned exercise, in place.

    Overwrites whatever the planner emitted: ``slot_id`` is an internal handle
    the service owns, and ids invented by an LLM could collide or repeat.
    """
    for day in plan.days:
        for planned in day.exercises:
            planned.slot_id = str(uuid4())


@rt.function_node
async def _run_pipeline(user_query: str) -> PlanResult:
    # 1. Intake: free text → UserProfile
    intake_output = await rt.call(Intake_Agent, user_query)
    profile: UserProfile = intake_output.structured
    logger.debug("Intake profile: %s", profile)

    # 2. Retrieve: profile → deduplicated exercise pool (5-way fan-out)
    exercises = cast(
        list[Exercise],
        await rt.call(rt.function_node(query_and_retrieve), profile),
    )
    logger.debug("Retrieved %d exercises", len(exercises))

    # Trim the pool before planning to reduce prompt noise.
    target_pool = profile.days_per_week * _POOL_PER_DAY
    exercises = exercises[:target_pool]
    logger.debug(
        "Pool trimmed to %d exercises (%d days × %d)",
        len(exercises),
        profile.days_per_week,
        _POOL_PER_DAY,
    )

    # 3. Plan: profile + trimmed pool → WorkoutPlan
    filtered_exercises = [
        {k: getattr(ex, k) for k in _PLANNER_FIELDS} for ex in exercises
    ]
    plan_query = {"profile": profile, "exercises": filtered_exercises}
    plan_output = await rt.call(Planner_Agent, str(plan_query))
    plan: WorkoutPlan = plan_output.structured

    # Give every occurrence its own stable handle so swaps can target one slot.
    _assign_slot_ids(plan)

    # Guard against hallucinated exercises before returning.
    validate_plan_exercise_ids(plan.model_dump(), exercises)

    return PlanResult(profile=profile, exercises=exercises, plan=plan)


async def generate_plan(user_query: str) -> PlanResult:
    """Run the full intake → retrieve → plan pipeline for a free-text request.

    Returns a :class:`PlanResult`. Raises ``ValueError`` if the planner
    references an exercise id outside the retrieved pool.
    """
    flow = rt.Flow("Generate Plan", entry_point=_run_pipeline)
    return await flow.ainvoke(user_query)
