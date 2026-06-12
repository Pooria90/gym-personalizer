import json
from pathlib import Path

import pytest

from gym_pt.config import get_settings
from gym_pt.models import UserProfile
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
