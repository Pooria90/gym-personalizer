"""Session model and storage seam.

A session is the stateful context a conversation needs: the profile, the
retrieved exercise pool (kept for swaps + plan validation), and the live
`WorkoutPlan`. `SessionStore` is the seam; `SnapshotSessionStore` is the
JSON-backed implementation for now, swapped for a relational store later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, Field

from gym_pt.models import Exercise, UserProfile, WorkoutPlan
from gym_pt.service.snapshot import JsonSnapshot


def _new_id() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Session(BaseModel):
    profile: UserProfile
    exercises: list[Exercise]  # retrieved pool; needed for swaps + id validation
    plan: WorkoutPlan  # live record of what the user is doing in the gym
    id: str = Field(default_factory=_new_id)
    created_at: datetime = Field(default_factory=_now)


@runtime_checkable
class SessionStore(Protocol):
    """Persistence contract for sessions (RQ-3 adds a relational impl)."""

    async def create(self, session: Session) -> None: ...
    async def get(self, session_id: str) -> Session | None: ...
    async def update(self, session: Session) -> None: ...


class SnapshotSessionStore:
    """`SessionStore` backed by a JSON snapshot. Single-process dev only.

    State loads from the snapshot on construction and flushes after every
    mutation. The flush is synchronous and runs with no intervening ``await``,
    so concurrent coroutines can't interleave a mutation with a serialization.
    """

    def __init__(self, snapshot: JsonSnapshot):
        self._snapshot = snapshot
        raw: dict[str, dict] = snapshot.load(default={})
        self._sessions: dict[str, Session] = {
            sid: Session.model_validate(data) for sid, data in raw.items()
        }

    async def create(self, session: Session) -> None:
        self._sessions[session.id] = session
        self._flush()

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def update(self, session: Session) -> None:
        self._sessions[session.id] = session
        self._flush()

    def _flush(self) -> None:
        self._snapshot.save(
            {sid: s.model_dump(mode="json") for sid, s in self._sessions.items()}
        )
