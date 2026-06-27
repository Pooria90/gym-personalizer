"""Service-layer exceptions.

Raised by the verbs in `service.py`; the API layer (RQ-5 step 4) maps them to
HTTP status codes (`SessionNotFound` → 404, the rest → 400/422).
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for service-layer errors."""


class SessionNotFound(ServiceError):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No session with id {session_id!r}")


class ExerciseNotInSession(ServiceError):
    """The exercise to swap is not part of this session's plan/pool."""

    def __init__(self, session_id: str, exercise_id: str):
        self.session_id = session_id
        self.exercise_id = exercise_id
        super().__init__(
            f"Exercise {exercise_id!r} is not in session {session_id!r}"
        )


class InvalidReplacement(ServiceError):
    """The chosen replacement is not among the current recommendations."""

    def __init__(self, exercise_id: str, replacement_id: str):
        self.exercise_id = exercise_id
        self.replacement_id = replacement_id
        super().__init__(
            f"{replacement_id!r} is not a current swap candidate for "
            f"{exercise_id!r}; re-fetch recommendations"
        )
