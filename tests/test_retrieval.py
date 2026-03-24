import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from gym_pt.models.exercise import Exercise
from gym_pt.models.plan import UserProfile
from gym_pt.railengine.query_protocol import DefaultSearchQueryBuilder
from gym_pt.railengine.retrieval import (
    filter_by_equipment,
    filter_by_level,
    search_exercises,
)


def _exercise(eid: str = "1", equipment: str = "cable", level: str = "beginner") -> Exercise:
    return Exercise(
        name="Cable Curl",
        force="pull",
        level=level,
        mechanic="isolation",
        equipment=equipment,
        primaryMuscles=["biceps"],
        secondaryMuscles=[],
        instructions=[],
        category="strength",
        images=[],
        id=eid,
    )


def test_default_search_query_builder():
    p = UserProfile(goal="strength", days_per_week=3)
    text = DefaultSearchQueryBuilder().build_query(p)
    assert "strength" in text
    assert "3 days per week" in text
    assert "intermediate" in text


def test_filter_by_equipment():
    items = [_exercise("1", "cable"), _exercise("2", "dumbbell")]
    got = filter_by_equipment(items, "cable")
    assert len(got) == 1 and got[0].id == "1"


def test_filter_by_level():
    items = [_exercise("1", level="beginner"), _exercise("2", level="advanced")]
    got = filter_by_level(items, "beginner")
    assert len(got) == 1 and got[0].id == "1"


def _fake_engine_factory(exercises: list[Exercise]):
    class _FakeEngine:
        engine_id = "test-engine"

        def __init__(self, *_a, **_kw) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def search_vector_store(self, **_kwargs):
            for ex in exercises:
                yield ex

    return _FakeEngine


async def _run_search_max():
    exercises = [_exercise(str(i)) for i in range(5)]
    settings = SimpleNamespace(engine_pat="pat", engine_id="eng")
    with (
        patch("gym_pt.railengine.retrieval.get_settings", return_value=settings),
        patch(
            "gym_pt.railengine.retrieval.Railengine",
            side_effect=_fake_engine_factory(exercises),
        ),
    ):
        out = await search_exercises("biceps", max_results=2, use_sdk_patch=False)
    assert len(out) == 2


def test_search_exercises_respects_max_results():
    asyncio.run(_run_search_max())
