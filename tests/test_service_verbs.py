"""Offline tests for service verbs. `generate_plan` is stubbed so these never
hit live LLM/retrieval APIs — they verify the persistence + memory wiring."""

import gym_pt.service.service as service_mod
from gym_pt.service import (
    JsonSnapshot,
    MemoryEventType,
    PlanResult,
    SnapshotMemory,
    SnapshotSessionStore,
    create_session,
)


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
