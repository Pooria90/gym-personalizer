"""Offline tests for the plan-generation pipeline's pure helpers."""

from gym_pt.models import PlannedExercise, WorkoutDay, WorkoutPlan
from gym_pt.service.pipeline import _assign_slot_ids


def _plan(**slot_ids) -> WorkoutPlan:
    """Two days, three planned exercises; optional explicit slot ids by name."""
    return WorkoutPlan(
        title="T",
        days=[
            WorkoutDay(
                day_index=1,
                exercises=[
                    PlannedExercise(
                        exercise_id="Barbell_Squat",
                        name="Barbell Squat",
                        **({"slot_id": slot_ids["a"]} if "a" in slot_ids else {}),
                    ),
                    PlannedExercise(
                        exercise_id="Push_Up",
                        name="Push Up",
                        **({"slot_id": slot_ids["b"]} if "b" in slot_ids else {}),
                    ),
                ],
            ),
            WorkoutDay(
                day_index=2,
                exercises=[
                    PlannedExercise(
                        exercise_id="Barbell_Squat",
                        name="Barbell Squat",
                        **({"slot_id": slot_ids["c"]} if "c" in slot_ids else {}),
                    ),
                ],
            ),
        ],
    )


class TestAssignSlotIds:
    def test_every_occurrence_gets_a_distinct_id(self):
        plan = _plan()
        _assign_slot_ids(plan)

        slots = [pe.slot_id for day in plan.days for pe in day.exercises]
        assert len(slots) == 3
        # The same exercise on two days must be addressable independently.
        assert len(set(slots)) == 3
        assert all(s for s in slots)

    def test_overwrites_ids_emitted_by_the_planner(self):
        # The planner sees slot_id in its output schema and may fill it in with
        # colliding or repeated values; the service owns these ids, not the LLM.
        plan = _plan(a="dupe", b="dupe", c="dupe")
        _assign_slot_ids(plan)

        slots = [pe.slot_id for day in plan.days for pe in day.exercises]
        assert "dupe" not in slots
        assert len(set(slots)) == 3
