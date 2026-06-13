"""Smoke: side-by-side backend parity report (migration plan, Phase 2).

Runs the five fixture query slots plus representative ad-hoc queries against
both backends and reports result counts, id overlap (Jaccard), and category
composition. Ranking differences are expected — the bar is "both backends
return sensible, non-empty pools", not identical lists. Run with:

    uv run pytest -m smoke tests/smoke/test_parity.py -s
"""

import json

import pytest

from gym_pt.retrieval import get_retriever
from tests.support import FIXTURES_DIR, needs_railengine, needs_railtracks_store

pytestmark = pytest.mark.smoke

AD_HOC_QUERIES = {
    "kettlebell_power": "explosive power exercises with kettlebell",
    "runner_mobility": "hip mobility and flexibility for runners",
    "home_bodyweight": "bodyweight only chest and triceps for home workout",
    "machine_legs": "leg machine exercises for muscle growth",
    "core_stability": "core stability anti-rotation exercises",
}

TOP_K = 8


@needs_railtracks_store
@needs_railengine
async def test_backend_parity_report():
    fixture_queries = json.loads(
        (FIXTURES_DIR / "sample_exercise_queries.json").read_text()
    )
    queries = {**fixture_queries, **AD_HOC_QUERIES}

    railtracks = await get_retriever("railtracks")
    railengine = await get_retriever("railengine")

    rows = []
    failures = []
    for slot, query in queries.items():
        rt_hits = await railtracks.search(query, max_results=TOP_K)
        re_hits = await railengine.search(query, max_results=TOP_K)

        rt_ids, re_ids = {e.id for e in rt_hits}, {e.id for e in re_hits}
        union = rt_ids | re_ids
        jaccard = len(rt_ids & re_ids) / len(union) if union else 0.0
        rt_cats = "/".join(sorted({e.category for e in rt_hits}))
        re_cats = "/".join(sorted({e.category for e in re_hits}))
        rows.append((slot, len(rt_hits), len(re_hits), jaccard, rt_cats, re_cats))

        if not rt_hits:
            failures.append(f"railtracks returned nothing for {slot!r}")
        if not re_hits:
            failures.append(f"railengine returned nothing for {slot!r}")

    header = (
        f"{'query slot':<20} {'rt':>3} {'re':>3} {'jaccard':>8}  categories (rt | re)"
    )
    print("\n" + header)
    print("-" * len(header))
    for slot, n_rt, n_re, jac, rt_cats, re_cats in rows:
        print(f"{slot:<20} {n_rt:>3} {n_re:>3} {jac:>8.2f}  {rt_cats} | {re_cats}")
    mean_jaccard = sum(r[3] for r in rows) / len(rows)
    print(f"\nmean Jaccard id-overlap: {mean_jaccard:.2f} across {len(rows)} queries")

    assert not failures, "; ".join(failures)
