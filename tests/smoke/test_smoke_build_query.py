"""Smoke: Query Agent in isolation (was scripts/smoke_build_query.py)."""

import pytest
import railtracks as rt

from gym_pt.agents import Query_Agent
from gym_pt.models import ExerciseQueries

pytestmark = pytest.mark.smoke


def test_query_agent_builds_all_query_slots(sample_profile):
    flow = rt.Flow(name="Query Agent", entry_point=Query_Agent)

    result = flow.invoke(str(sample_profile))
    queries = result.structured

    assert isinstance(queries, ExerciseQueries)
    for field_name in ExerciseQueries.model_fields:
        assert getattr(queries, field_name).strip(), f"{field_name} is empty"
