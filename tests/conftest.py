import json
from pathlib import Path

import pytest

from gym_pt.config import get_settings
from gym_pt.models import (
    PlannedExercise,
    UserProfile,
    WorkoutDay,
    WorkoutPlan,
)
from gym_pt.service import Session
from tests.support import FIXTURES_DIR, make_exercise


@pytest.fixture(scope="session", autouse=True)
def _load_env() -> None:
    """Load gym/.env into os.environ once so SDKs find credentials."""
    get_settings()


@pytest.fixture
def sample_profile() -> UserProfile:
    raw = json.loads((FIXTURES_DIR / "sample_profile.json").read_text())
    return UserProfile.model_validate(raw)


@pytest.fixture
def exercise_factory():
    return make_exercise


@pytest.fixture
def tiny_dataset(tmp_path: Path):
    """Write a 4-exercise dataset file and return (path, catalog dict)."""
    exercises = [
        make_exercise(
            "Barbell_Squat",
            name="Barbell Squat",
            equipment="barbell",
            primaryMuscles=["quadriceps"],
            category="strength",
            instructions=["Squat down keeping your back straight.", "Drive up."],
        ),
        make_exercise(
            "Push_Up",
            name="Push Up",
            equipment=None,
            primaryMuscles=["chest"],
            category="strength",
            instructions=["Lower your body to the floor and push back up."],
        ),
        make_exercise(
            "Hamstring_Stretch",
            name="Hamstring Stretch",
            equipment=None,
            primaryMuscles=["hamstrings"],
            category="stretching",
            instructions=["Reach gently toward your toes and hold."],
        ),
        make_exercise(
            "Treadmill_Run",
            name="Treadmill Run",
            equipment="machine",
            primaryMuscles=["quadriceps"],
            category="cardio",
            instructions=["Run at a steady conversational pace."],
        ),
    ]
    path = tmp_path / "exercises.json"
    path.write_text(json.dumps([ex.model_dump() for ex in exercises]))
    return path, {ex.id: ex for ex in exercises}


@pytest.fixture
def sample_session(sample_profile) -> Session:
    """A small, self-consistent Session (plan references the pooled exercises).

    Barbell Squat is planned on both days, with fixed ``slot_id``s, so tests can
    prove a swap lands on exactly one occurrence and leaves the other alone.
    """
    exercises = [
        make_exercise("Barbell_Squat", name="Barbell Squat", equipment="barbell"),
        make_exercise("Push_Up", name="Push Up", equipment=None),
    ]
    plan = WorkoutPlan(
        title="Test Plan",
        days=[
            WorkoutDay(
                day_index=1,
                focus="full body",
                exercises=[
                    PlannedExercise(
                        slot_id="slot-squat-d1",
                        exercise_id="Barbell_Squat",
                        name="Barbell Squat",
                        sets=3,
                        reps="5",
                    ),
                    PlannedExercise(
                        slot_id="slot-pushup-d1",
                        exercise_id="Push_Up",
                        name="Push Up",
                        sets=3,
                        reps="10",
                    ),
                ],
            ),
            WorkoutDay(
                day_index=2,
                focus="lower body",
                exercises=[
                    PlannedExercise(
                        slot_id="slot-squat-d2",
                        exercise_id="Barbell_Squat",
                        name="Barbell Squat",
                        sets=5,
                        reps="3",
                    ),
                ],
            ),
        ],
    )
    return Session(profile=sample_profile, exercises=exercises, plan=plan)
