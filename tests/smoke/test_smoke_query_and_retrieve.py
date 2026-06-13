"""Smoke: Query Agent + retrieval fan-out (was scripts/smoke_query_and_retrieve.py)."""

import pytest
import railtracks as rt

from tests.support import needs_railtracks_store
from gym_pt.agents import query_and_retrieve
from gym_pt.models import Exercise

pytestmark = pytest.mark.smoke


@needs_railtracks_store
def test_query_and_retrieve_builds_deduplicated_pool(sample_profile):
    flow = rt.Flow(
        "Query and Retrieve", entry_point=rt.function_node(query_and_retrieve)
    )

    exercises = flow.invoke(sample_profile)

    assert exercises, "empty exercise pool"
    assert all(isinstance(ex, Exercise) for ex in exercises)
    assert len({ex.id for ex in exercises}) == len(exercises), "pool not deduplicated"
    # Budget is days_per_week * 8; per-slot rounding can add a little slack
    assert len(exercises) <= sample_profile.days_per_week * 8 + 3
