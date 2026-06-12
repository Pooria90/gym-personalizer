"""Smoke: vector search through the retriever seam (was scripts/smoke_retrieval.py)."""

import pytest

from tests.support import needs_railengine, needs_railtracks_store
from gym_pt.models import Exercise
from gym_pt.retrieval import get_retriever

pytestmark = pytest.mark.smoke

QUERY = "exercises for biceps with cables"


@needs_railtracks_store
async def test_railtracks_backend_search():
    retriever = await get_retriever("railtracks")
    results = await retriever.search(QUERY, max_results=5)

    assert results, "no results from railtracks backend"
    assert all(isinstance(ex, Exercise) for ex in results)
    assert len({ex.id for ex in results}) == len(results)


@needs_railengine
async def test_railengine_backend_search():
    retriever = await get_retriever("railengine")
    results = await retriever.search(QUERY, max_results=5)

    assert results, "no results from railengine backend"
    assert all(isinstance(ex, Exercise) for ex in results)
