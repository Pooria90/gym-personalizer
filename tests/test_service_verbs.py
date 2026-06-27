"""Offline tests for service verbs. `generate_plan` and the `swap_exercise`
tool are stubbed so these never hit live LLM/retrieval APIs — they verify the
persistence, memory, and plan-mutation wiring."""

import pytest

import gym_pt.service.service as service_mod
from gym_pt.service import (
    ExerciseNotInSession,
    InvalidReplacement,
    JsonSnapshot,
    MemoryEventType,
    PlanResult,
    SessionNotFound,
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
    async def fake_swap(exercise, profile, *, max_candidates=3):
        return candidates[:max_candidates]

    monkeypatch.setattr(service_mod, "swap_exercise", fake_swap)


class TestRecommendSwaps:
    async def test_returns_candidates(self, tmp_path, monkeypatch, sample_session):
        candidates = [make_exercise("Goblet_Squat"), make_exercise("Hack_Squat")]
        _stub_swap_tool(monkeypatch, candidates)
        store = _store(tmp_path)
        await store.create(sample_session)

        result = await recommend_swaps(
            sample_session.id, "Barbell_Squat", store=store
        )
        assert [e.id for e in result] == ["Goblet_Squat", "Hack_Squat"]

    async def test_exercise_not_in_pool_raises(
        self, tmp_path, monkeypatch, sample_session
    ):
        _stub_swap_tool(monkeypatch, [])
        store = _store(tmp_path)
        await store.create(sample_session)
        with pytest.raises(ExerciseNotInSession):
            await recommend_swaps(sample_session.id, "Not_In_Pool", store=store)

    async def test_unknown_session_raises(self, tmp_path, monkeypatch):
        _stub_swap_tool(monkeypatch, [])
        with pytest.raises(SessionNotFound):
            await recommend_swaps("nope", "Barbell_Squat", store=_store(tmp_path))


class TestApplySwap:
    async def test_mutates_plan_and_records_event(
        self, tmp_path, monkeypatch, sample_session
    ):
        replacement = make_exercise("Goblet_Squat", name="Goblet Squat")
        _stub_swap_tool(monkeypatch, [replacement])
        store = _store(tmp_path)
        memory = _memory(tmp_path)
        await store.create(sample_session)

        plan = await apply_swap(
            sample_session.id,
            "Barbell_Squat",
            "Goblet_Squat",
            store=store,
            memory=memory,
        )

        # plan now references the replacement, with the prescription preserved
        planned = [pe for day in plan.days for pe in day.exercises]
        squat = next(pe for pe in planned if pe.exercise_id == "Goblet_Squat")
        assert squat.name == "Goblet Squat"
        assert squat.sets == 3 and squat.reps == "5"
        assert all(pe.exercise_id != "Barbell_Squat" for pe in planned)

        # replacement added to the pool so the plan stays valid
        assert "Goblet_Squat" in {ex.id for ex in (await store.get(sample_session.id)).exercises}

        # SWAP_APPLIED event with ids-only payload
        events = await memory.history()
        assert events[-1].type == MemoryEventType.SWAP_APPLIED
        assert events[-1].payload == {
            "from": "Barbell_Squat",
            "to": "Goblet_Squat",
            "occurrences": 1,
        }

    async def test_invalid_replacement_raises(
        self, tmp_path, monkeypatch, sample_session
    ):
        _stub_swap_tool(monkeypatch, [make_exercise("Goblet_Squat")])
        store = _store(tmp_path)
        memory = _memory(tmp_path)
        await store.create(sample_session)
        with pytest.raises(InvalidReplacement):
            await apply_swap(
                sample_session.id,
                "Barbell_Squat",
                "Not_A_Candidate",
                store=store,
                memory=memory,
            )

    async def test_persists_mutation_across_reopen(
        self, tmp_path, monkeypatch, sample_session
    ):
        _stub_swap_tool(monkeypatch, [make_exercise("Goblet_Squat")])
        sessions_path = tmp_path / "sessions.json"
        store = SnapshotSessionStore(JsonSnapshot(sessions_path))
        memory = _memory(tmp_path)
        await store.create(sample_session)
        await apply_swap(
            sample_session.id,
            "Barbell_Squat",
            "Goblet_Squat",
            store=store,
            memory=memory,
        )

        reopened = SnapshotSessionStore(JsonSnapshot(sessions_path))
        plan = await get_plan(sample_session.id, store=reopened)
        planned_ids = {pe.exercise_id for day in plan.days for pe in day.exercises}
        assert "Goblet_Squat" in planned_ids
        assert "Barbell_Squat" not in planned_ids
