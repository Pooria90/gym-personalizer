"""Offline tests for the service persistence seams: JSON snapshot primitive,
SnapshotSessionStore, and SnapshotMemory. No network, no live APIs."""

from gym_pt.service import (
    JsonSnapshot,
    Memory,
    MemoryEvent,
    MemoryEventType,
    SessionStore,
    SnapshotMemory,
    SnapshotSessionStore,
)


class TestJsonSnapshot:
    def test_load_default_when_file_absent(self, tmp_path):
        snap = JsonSnapshot(tmp_path / "missing.json")
        assert snap.load(default={}) == {}
        assert snap.load(default=[]) == []

    def test_save_then_load_round_trip(self, tmp_path):
        snap = JsonSnapshot(tmp_path / "state.json")
        snap.save({"a": 1, "nested": {"b": [1, 2, 3]}})
        assert JsonSnapshot(tmp_path / "state.json").load(default={}) == {
            "a": 1,
            "nested": {"b": [1, 2, 3]},
        }

    def test_save_overwrites(self, tmp_path):
        snap = JsonSnapshot(tmp_path / "state.json")
        snap.save({"v": 1})
        snap.save({"v": 2})
        assert snap.load(default={}) == {"v": 2}

    def test_save_creates_parent_dirs_and_leaves_no_tmp(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "state.json"
        JsonSnapshot(target).save({"ok": True})
        assert target.exists()
        # atomic write must not leave the temp file behind
        assert not (target.parent / (target.name + ".tmp")).exists()


class TestSnapshotSessionStore:
    def test_satisfies_protocol(self, tmp_path):
        store = SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))
        assert isinstance(store, SessionStore)

    async def test_create_and_get(self, tmp_path, sample_session):
        store = SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))
        await store.create(sample_session)
        fetched = await store.get(sample_session.id)
        assert fetched is not None
        assert fetched.id == sample_session.id
        assert fetched.plan.title == sample_session.plan.title

    async def test_get_missing_returns_none(self, tmp_path):
        store = SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))
        assert await store.get("nope") is None

    async def test_update_mutates_in_place(self, tmp_path, sample_session):
        store = SnapshotSessionStore(JsonSnapshot(tmp_path / "sessions.json"))
        await store.create(sample_session)
        sample_session.plan.title = "Changed"
        await store.update(sample_session)
        fetched = await store.get(sample_session.id)
        assert fetched.plan.title == "Changed"

    async def test_persists_across_reopen(self, tmp_path, sample_session):
        path = tmp_path / "sessions.json"
        store = SnapshotSessionStore(JsonSnapshot(path))
        await store.create(sample_session)

        # A fresh store reading the same file sees the session (restart-safe).
        reopened = SnapshotSessionStore(JsonSnapshot(path))
        fetched = await reopened.get(sample_session.id)
        assert fetched is not None
        assert fetched.profile.days_per_week == sample_session.profile.days_per_week
        assert [e.id for e in fetched.exercises] == [
            e.id for e in sample_session.exercises
        ]


class TestSnapshotMemory:
    def test_satisfies_protocol(self, tmp_path):
        mem = SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))
        assert isinstance(mem, Memory)

    async def test_record_and_history_preserves_order(self, tmp_path):
        mem = SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))
        await mem.record(
            MemoryEvent(type=MemoryEventType.PLAN_CREATED, session_id="s1")
        )
        await mem.record(
            MemoryEvent(
                type=MemoryEventType.SWAP_APPLIED,
                session_id="s1",
                payload={"from": "A", "to": "B"},
            )
        )
        events = await mem.history()
        assert [e.type for e in events] == [
            MemoryEventType.PLAN_CREATED,
            MemoryEventType.SWAP_APPLIED,
        ]
        assert events[1].payload == {"from": "A", "to": "B"}

    async def test_history_limit_returns_most_recent(self, tmp_path):
        mem = SnapshotMemory(JsonSnapshot(tmp_path / "memory.json"))
        for i in range(5):
            await mem.record(
                MemoryEvent(type=MemoryEventType.PLAN_CREATED, session_id=f"s{i}")
            )
        recent = await mem.history(limit=2)
        assert [e.session_id for e in recent] == ["s3", "s4"]

    async def test_persists_across_reopen(self, tmp_path):
        path = tmp_path / "memory.json"
        mem = SnapshotMemory(JsonSnapshot(path))
        await mem.record(
            MemoryEvent(type=MemoryEventType.PLAN_CREATED, session_id="s1")
        )
        reopened = SnapshotMemory(JsonSnapshot(path))
        history = await reopened.history()
        assert len(history) == 1
        assert history[0].session_id == "s1"
