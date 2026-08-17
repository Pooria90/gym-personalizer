"""Service-layer exceptions.

Raised by the verbs in `service.py`; the API layer maps them to
HTTP status codes (`SessionNotFound` → 404, the rest → 400/422).
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for service-layer errors."""


class SessionNotFound(ServiceError):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No session with id {session_id!r}")


class SlotNotFound(ServiceError):
    """No planned exercise in this session carries that ``slot_id``."""

    def __init__(self, session_id: str, slot_id: str):
        self.session_id = session_id
        self.slot_id = slot_id
        super().__init__(
            f"Session {session_id!r} has no planned exercise with slot id "
            f"{slot_id!r}"
        )


class ExerciseNotInSession(ServiceError):
    """A planned exercise is missing from the session's retrieved pool.

    An invariant breach rather than a user error: `create_session` validates
    that every planned id came from the pool, and `apply_swap` adds each
    replacement to it.
    """

    def __init__(self, session_id: str, exercise_id: str):
        self.session_id = session_id
        self.exercise_id = exercise_id
        super().__init__(
            f"Exercise {exercise_id!r} is planned in session {session_id!r} "
            "but absent from its retrieved pool"
        )


class NoPendingRecommendations(ServiceError):
    """Nothing has been recommended for this slot yet (or it was consumed)."""

    def __init__(self, session_id: str, slot_id: str):
        self.session_id = session_id
        self.slot_id = slot_id
        super().__init__(
            f"No swap recommendations pending for slot {slot_id!r} in session "
            f"{session_id!r}; request recommendations first"
        )


class InvalidReplacement(ServiceError):
    """The chosen replacement is not among the recommendations for this slot."""

    def __init__(self, slot_id: str, replacement_id: str):
        self.slot_id = slot_id
        self.replacement_id = replacement_id
        super().__init__(
            f"{replacement_id!r} is not a current swap candidate for slot "
            f"{slot_id!r}; re-fetch recommendations"
        )
