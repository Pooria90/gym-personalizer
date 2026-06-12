from gym_pt.agents.tools import _compute_top_k
from gym_pt.models import ExerciseQueries, UserProfile


def _profile(days: int) -> UserProfile:
    return UserProfile.model_validate(
        {
            "goal": "strength",
            "days_per_week": days,
            "equipment": ["dumbbell"],
            "level": "beginner",
        }
    )


def test_covers_every_query_field():
    top_k = _compute_top_k(_profile(3))
    assert set(top_k) == set(ExerciseQueries.model_fields)


def test_three_day_distribution_matches_docstring():
    assert _compute_top_k(_profile(3)) == {
        "warmup_query": 5,
        "primary_query": 6,
        "secondary_query": 7,
        "equipment_query": 3,
        "cooldown_query": 3,
    }


def test_two_day_distribution_matches_docstring():
    assert _compute_top_k(_profile(2)) == {
        "warmup_query": 3,
        "primary_query": 4,
        "secondary_query": 5,
        "equipment_query": 2,
        "cooldown_query": 2,
    }


def test_budget_scales_with_days_and_floors_at_one():
    for days in range(1, 8):
        top_k = _compute_top_k(_profile(days))
        budget = days * 8
        assert all(k >= 1 for k in top_k.values())
        # Per-slot rounding can drift the sum slightly; never by more than
        # half a unit per slot.
        assert abs(sum(top_k.values()) - budget) <= len(top_k) // 2


def test_more_days_never_shrinks_a_slot():
    small = _compute_top_k(_profile(2))
    large = _compute_top_k(_profile(6))
    assert all(large[name] >= small[name] for name in small)
