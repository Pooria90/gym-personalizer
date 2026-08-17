"""Offline tests for service verbs. `generate_plan` and the `swap_exercise`
tool are stubbed so these never hit live LLM/retrieval APIs — they verify the
persistence, memory, and plan-mutation wiring."""

import pytest

import gym_pt.service.service as service_mod
from gym_pt.service import (
    InvalidReplacement,
    JsonSnapshot,
    MemoryEventType,
    NoPendingRecommendations,
    PlanResult,
    SessionNotFound,
    SlotNotFound,
    SnapshotMemory,
    SnapshotSessionStore,
    apply_swap,
    create_session,
    get_plan,
    recommend_swaps,
)
from tests.support import make_exercise


def _store(tmp_path):
    return SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))


def _memory(tmp_path):
    return SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))


def _stub_generate_plan(monkeypatch, sample_session):
    canned = PlanResult(
        profile=sample_session.profile,
        exercises=sample_session.exercises,
        plan=sample_session.plan,
    )

    async def fake_generate_plan(user_query: str) -> PlanResult:
        return canned

    monkeypatch.setattr(service_mod, "generate_plan", fake_generate_plan)
    return canned


class TestCreateSession:
    async def test_persists_session_and_records_memory(
        self, tmp_path, monkeypatch, sample_session
    ):
        canned = _stub_generate_plan(monkeypatch, sample_session)
        store = SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))
        memory = SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))

        session = await create_session("any text", store=store, memory=memory)

        # session persisted and carries the generated plan
        assert await store.get(session.id) is not None
        assert session.plan.title == canned.plan.title

        # exactly one PLAN_CREATED memory event, tied to this session, ids only
        events = await memory.history()
        assert len(events) == 1
        assert events[0].type == MemoryEventType.PLAN_CREATED
        assert events[0].session_id == session.id
        assert events[0].payload["exercise_ids"] == [
            pe.exercise_id
            for day in session.plan.days
            for pe in day.exercises
        ]

    async def test_survives_reopen(self, tmp_path, monkeypatch, sample_session):
        _stub_generate_plan(monkeypatch, sample_session)
        sessions_path = tmp_path / "sessions.json"
        store = SnapshotSessionStore(JsonSnapshot(sessions_path))
        memory = SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))

        session = await create_session("any text", store=store, memory=memory)

        reopened = SnapshotSessionStore(JsonSnapshot(sessions_path))
        assert await reopened.get(session.id) is not None


class TestGetPlan:
    async def test_returns_session_plan(self, tmp_path, sample_session):
        store = _store(tmp_path)
        await store.create(sample_session)
        plan = await get_plan(sample_session.id, store=store)
        assert plan.title == sample_session.plan.title

    async def test_unknown_session_raises(self, tmp_path):
        with pytest.raises(SessionNotFound):
            await get_plan("nope", store=_store(tmp_path))


def _stub_swap_tool(monkeypatch, candidates):
    async def fake_swap(exercise, profile):
        return list(candidates)

    monkeypatch.setattr(service_mod, "swap_exercise", fake_swap)


def _slot(plan, slot_id):
    return next(
        pe for day in plan.days for pe in day.exercises if pe.slot_id == slot_id
    )


class TestRecommendSwaps:
    async def test_returns_and_stashes_candidates(
        self, tmp_path, monkeypatch, sample_session
    ):
        candidates = [make_exercise("Goblet_Squat"), make_exercise("Hack_Squat")]
        _stub_swap_tool(monkeypatch, candidates)
        store = _store(tmp_path)
        await store.create(sample_session)

        result = await recommend_swaps(
            sample_session.id, "slot-squat-d1", store=store
        )
        assert [e.id for e in result] == ["Goblet_Squat", "Hack_Squat"]

        # stashed on the session so apply_swap needs no second retrieval
        stored = await store.get(sample_session.id)
        assert [e.id for e in stored.pending_swaps["slot-squat-d1"]] == [
            "Goblet_Squat",
            "Hack_Squat",
        ]

    async def test_leaves_plan_untouched(
        self, tmp_path, monkeypatch, sample_session
    ):
        _stub_swap_tool(monkeypatch, [make_exercise("Goblet_Squat")])
        store = _store(tmp_path)
        await store.create(sample_session)

        await recommend_swaps(sample_session.id, "slot-squat-d1", store=store)

        plan = await get_plan(sample_session.id, store=store)
        assert _slot(plan, "slot-squat-d1").exercise_id == "Barbell_Squat"

    async def test_unknown_slot_raises(
        self, tmp_path, monkeypatch, sample_session
    ):
        _stub_swap_tool(monkeypatch, [])
        store = _store(tmp_path)
        await store.create(sample_session)
        with pytest.raises(SlotNotFound):
            await recommend_swaps(sample_session.id, "no-such-slot", store=store)

    async def test_unknown_session_raises(self, tmp_path, monkeypatch):
        _stub_swap_tool(monkeypatch, [])
        with pytest.raises(SessionNotFound):
            await recommend_swaps("nope", "slot-squat-d1", store=_store(tmp_path))


class TestApplySwap:
    async def _recommend(self, monkeypatch, store, session, slot_id, candidates):
        _stub_swap_tool(monkeypatch, candidates)
        await recommend_swaps(session.id, slot_id, store=store)

    async def test_swaps_one_occurrence_only(
        self, tmp_path, monkeypatch, sample_session
    ):
        replacement = make_exercise("Goblet_Squat", name="Goblet Squat")
        store = _store(tmp_path)
        memory = _memory(tmp_path)
        await store.create(sample_session)
        await self._recommend(
            monkeypatch, store, sample_session, "slot-squat-d1", [replacement]
        )

        plan = await apply_swap(
            sample_session.id,
            "slot-squat-d1",
            "Goblet_Squat",
            store=store,
            memory=memory,
        )

        # the targeted slot changed movement but kept its prescription
        swapped = _slot(plan, "slot-squat-d1")
        assert swapped.exercise_id == "Goblet_Squat"
        assert swapped.name == "Goblet Squat"
        assert swapped.sets == 3 and swapped.reps == "5"

        # the same exercise on day 2 is untouched — this is the whole point
        untouched = _slot(plan, "slot-squat-d2")
        assert untouched.exercise_id == "Barbell_Squat"
        assert untouched.sets == 5 and untouched.reps == "3"

    async def test_updates_pool_memory_and_clears_pending(
        self, tmp_path, monkeypatch, sample_session
    ):
        store = _store(tmp_path)
        memory = _memory(tmp_path)
        await store.create(sample_session)
        await self._recommend(
            monkeypatch,
            store,
            sample_session,
            "slot-squat-d1",
            [make_exercise("Goblet_Squat", name="Goblet Squat")],
        )

        await apply_swap(
            sample_session.id,
            "slot-squat-d1",
            "Goblet_Squat",
            store=store,
            memory=memory,
        )

        stored = await store.get(sample_session.id)
        # replacement joined the pool so the plan stays valid
        assert "Goblet_Squat" in {ex.id for ex in stored.exercises}
        # recommendations consumed — they describe a movement no longer there
        assert "slot-squat-d1" not in stored.pending_swaps

        events = await memory.history()
        assert events[-1].type == MemoryEventType.SWAP_APPLIED
        assert events[-1].payload == {
            "slot_id": "slot-squat-d1",
            "from": "Barbell_Squat",
            "to": "Goblet_Squat",
        }

    async def test_reapplying_is_a_noop(
        self, tmp_path, monkeypatch, sample_session
    ):
        store = _store(tmp_path)
        memory = _memory(tmp_path)
        await store.create(sample_session)
        await self._recommend(
            monkeypatch,
            store,
            sample_session,
            "slot-squat-d1",
            [make_exercise("Goblet_Squat", name="Goblet Squat")],
        )
        args = (sample_session.id, "slot-squat-d1", "Goblet_Squat")
        await apply_swap(*args, store=store, memory=memory)

        # a retried request must not fail, and must not double-log
        plan = await apply_swap(*args, store=store, memory=memory)

        assert _slot(plan, "slot-squat-d1").exercise_id == "Goblet_Squat"
        swap_events = [
            e
            for e in await memory.history()
            if e.type == MemoryEventType.SWAP_APPLIED
        ]
        assert len(swap_events) == 1

    async def test_without_recommendations_raises(
        self, tmp_path, sample_session
    ):
        store = _store(tmp_path)
        await store.create(sample_session)
        with pytest.raises(NoPendingRecommendations):
            await apply_swap(
                sample_session.id,
                "slot-squat-d1",
                "Goblet_Squat",
                store=store,
                memory=_memory(tmp_path),
            )

    async def test_replacement_outside_recommendations_raises(
        self, tmp_path, monkeypatch, sample_session
    ):
        store = _store(tmp_path)
        await store.create(sample_session)
        await self._recommend(
            monkeypatch,
            store,
            sample_session,
            "slot-squat-d1",
            [make_exercise("Goblet_Squat")],
        )
        with pytest.raises(InvalidReplacement):
            await apply_swap(
                sample_session.id,
                "slot-squat-d1",
                "Not_A_Candidate",
                store=store,
                memory=_memory(tmp_path),
            )

    async def test_unknown_slot_raises(self, tmp_path, sample_session):
        store = _store(tmp_path)
        await store.create(sample_session)
        with pytest.raises(SlotNotFound):
            await apply_swap(
                sample_session.id,
                "no-such-slot",
                "Goblet_Squat",
                store=store,
                memory=_memory(tmp_path),
            )

    async def test_persists_mutation_across_reopen(
        self, tmp_path, monkeypatch, sample_session
    ):
        sessions_path = tmp_path / "sessions.json"
        store = SnapshotSessionStore(JsonSnapshot(sessions_path))
        memory = _memory(tmp_path)
        await store.create(sample_session)
        await self._recommend(
            monkeypatch,
            store,
            sample_session,
            "slot-squat-d1",
            [make_exercise("Goblet_Squat", name="Goblet Squat")],
        )
        await apply_swap(
            sample_session.id,
            "slot-squat-d1",
            "Goblet_Squat",
            store=store,
            memory=memory,
        )

        reopened = SnapshotSessionStore(JsonSnapshot(sessions_path))
        plan = await get_plan(sample_session.id, store=reopened)
        assert _slot(plan, "slot-squat-d1").exercise_id == "Goblet_Squat"
        assert _slot(plan, "slot-squat-d2").exercise_id == "Barbell_Squat"
