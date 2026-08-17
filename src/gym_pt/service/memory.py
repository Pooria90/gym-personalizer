"""Memory seam: the durable record of what the user does in the gym.

Distinct from a session: memory spans sessions (plans generated, swaps made).
NOTE: For now, we define a minimal protocol and back it with a JSON snapshot.
Later, an adapter implements `Memory` and replaces `SnapshotMemory` 
with no caller changes.

Events stay small by design: an event type, the session it belongs to, a
timestamp, and a payload of ids; not full plan/exercise objects.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryEventType(str, Enum):
    PLAN_CREATED = "plan_created"
    SWAP_APPLIED = "swap_applied"


class MemoryEvent(BaseModel):
    type: MemoryEventType
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)  # ids, not full objects
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@runtime_checkable
class Memory(Protocol):
    """Append-only activity log (swap target: native Railtracks memory)."""

    async def record(self, event: MemoryEvent) -> None: ...
    async def history(self, *, limit: int | None = None) -> list[MemoryEvent]: ...


class SnapshotMemory:
    """`Memory` backed by a JSON snapshot. Process-global until user-based storage is implemented."""

    def __init__(self, snapshot):
        self._snapshot = snapshot
        raw: list[dict] = snapshot.load(default=[])
        self._events: list[MemoryEvent] = [
            MemoryEvent.model_validate(e) for e in raw
        ]

    async def record(self, event: MemoryEvent) -> None:
        self._events.append(event)
        self._flush()

    async def history(self, *, limit: int | None = None) -> list[MemoryEvent]:
        events = self._events[-limit:] if limit is not None else self._events
        return list(events)

    def _flush(self) -> None:
        self._snapshot.save([e.model_dump(mode="json") for e in self._events])
