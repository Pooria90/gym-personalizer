"""Smoke: Planner Agent with a fixed exercise pool (was scripts/smoke_plan.py)."""

import json

import pytest
import railtracks as rt

from tests.support import FIXTURES_DIR
from gym_pt.agents import Planner_Agent
from gym_pt.models import WorkoutPlan

pytestmark = pytest.mark.smoke

FIELDS_TO_KEEP = ["id", "equipment", "primaryMuscles", "secondaryMuscles", "category"]


def test_planner_agent_uses_only_pool_exercises(sample_profile):
    exercises = json.loads(
        (FIXTURES_DIR / "sample_retrieved_exercises.json").read_text()
    )
    filtered = [{k: ex.get(k) for k in FIELDS_TO_KEEP} for ex in exercises]
    flow = rt.Flow(name="Planner Agent", entry_point=Planner_Agent)

    result = flow.invoke(str({"profile": sample_profile, "exercises": filtered}))
    plan = result.structured

    assert isinstance(plan, WorkoutPlan)
    assert len(plan.days) == sample_profile.days_per_week

    pool_ids = {ex["id"] for ex in exercises}
    planned_ids = {
        planned.exercise_id for day in plan.days for planned in day.exercises
    }
    assert planned_ids, "plan contains no exercises"
    assert planned_ids <= pool_ids, f"hallucinated ids: {planned_ids - pool_ids}"
