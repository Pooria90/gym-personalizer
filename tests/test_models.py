from gym_pt.models import Exercise, UserProfile, WorkoutPlan
from gym_pt.models.plan import FitnessLevel


def test_exercise_roundtrip():
    raw = {
        "name": "Cable Curl",
        "force": "pull",
        "level": "beginner",
        "mechanic": "isolation",
        "equipment": "cable",
        "primaryMuscles": ["biceps"],
        "secondaryMuscles": [],
        "instructions": ["Keep elbows still."],
        "category": "strength",
        "images": [],
        "id": "ex-1",
    }
    ex = Exercise.model_validate(raw)
    assert ex.id == "ex-1"
    assert ex.name == "Cable Curl"


def test_user_profile_defaults():
    p = UserProfile(goal="strength", days_per_week=3)
    assert p.level == FitnessLevel.INTERMEDIATE
    assert p.equipment == []


def test_workout_plan_empty():
    plan = WorkoutPlan()
    assert plan.days == []
