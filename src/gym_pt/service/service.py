"""Shared service verbs — the operations both the CLI and the API call.

No HTTP here. Stores are passed in (dependency injection) so the caller owns
persistence lifecycle: the CLI builds snapshot-backed stores per run; the API
will reuse singletons built at startup.
"""

from __future__ import annotations

import logging

from gym_pt.agents import swap_exercise
from gym_pt.models import Exercise, WorkoutPlan
from gym_pt.service.errors import (
    ExerciseNotInSession,
    InvalidReplacement,
    SessionNotFound,
)
from gym_pt.service.memory import Memory, MemoryEvent, MemoryEventType
from gym_pt.service.pipeline import generate_plan
from gym_pt.service.sessions import Session, SessionStore

logger = logging.getLogger("gym_pt.service")


async def create_session(
    user_query: str,
    *,
    store: SessionStore,
    memory: Memory,
) -> Session:
    """Run the pipeline for a free-text request, persist the session, log it.

    Wraps the `PlanResult` in a `Session` (the live record of what the user is
    doing), persists it, and records a `PLAN_CREATED` memory event carrying only
    ids/counts — not the full plan, which already lives on the session.
    """
    result = await generate_plan(user_query)
    session = Session(
        profile=result.profile,
        exercises=result.exercises,
        plan=result.plan,
    )
    await store.create(session)
    await memory.record(
        MemoryEvent(
            type=MemoryEventType.PLAN_CREATED,
            session_id=session.id,
            payload={
                "title": session.plan.title,
                "days": len(session.plan.days),
                "exercise_ids": [
                    pe.exercise_id
                    for day in session.plan.days
                    for pe in day.exercises
                ],
            },
        )
    )
    logger.info(
        "Created session %s (%d-day plan, %d planned exercises)",
        session.id,
        len(session.plan.days),
        sum(len(d.exercises) for d in session.plan.days),
    )
    return session


async def _require_session(session_id: str, store: SessionStore) -> Session:
    session = await store.get(session_id)
    if session is None:
        raise SessionNotFound(session_id)
    return session


def _find_in_pool(session: Session, exercise_id: str) -> Exercise:
    for ex in session.exercises:
        if ex.id == exercise_id:
            return ex
    raise ExerciseNotInSession(session.id, exercise_id)


async def _candidates(
    session: Session, exercise_id: str, max_candidates: int
) -> list[Exercise]:
    target = _find_in_pool(session, exercise_id)
    return await swap_exercise(
        target, session.profile, max_candidates=max_candidates
    )


async def get_plan(session_id: str, *, store: SessionStore) -> WorkoutPlan:
    """Return the current plan for a session. Raises `SessionNotFound`."""
    session = await _require_session(session_id, store)
    return session.plan


async def recommend_swaps(
    session_id: str,
    exercise_id: str,
    *,
    store: SessionStore,
    max_candidates: int = 3,
) -> list[Exercise]:
    """Suggest replacements for one planned exercise — does not change the plan.

    Raises `SessionNotFound` / `ExerciseNotInSession`.
    """
    session = await _require_session(session_id, store)
    return await _candidates(session, exercise_id, max_candidates)


async def apply_swap(
    session_id: str,
    exercise_id: str,
    replacement_id: str,
    *,
    store: SessionStore,
    memory: Memory,
    max_candidates: int = 3,
) -> WorkoutPlan:
    """Replace one exercise with a chosen recommendation, in place.

    Mutates every occurrence of ``exercise_id`` in the stored `WorkoutPlan`
    (the prescription — sets/reps — is kept; only the movement changes), adds
    the replacement to the session pool so the plan stays valid, persists the
    session, and records a `SWAP_APPLIED` event. Does **not** re-run intake or
    the planner — only one exercise changes.

    ``replacement_id`` must be one of the current recommendations; the candidate
    set is re-derived here (one retrieval call, same ``max_candidates``) so the
    chosen replacement arrives as a full `Exercise` without a backend-specific
    by-id lookup. Raises `SessionNotFound` / `ExerciseNotInSession` /
    `InvalidReplacement`.
    """
    session = await _require_session(session_id, store)
    candidates = await _candidates(session, exercise_id, max_candidates)
    replacement = next((c for c in candidates if c.id == replacement_id), None)
    if replacement is None:
        raise InvalidReplacement(exercise_id, replacement_id)

    occurrences = _replace_in_plan(session.plan, exercise_id, replacement)
    if occurrences == 0:
        # In the pool but not actually planned — nothing to swap.
        raise ExerciseNotInSession(session.id, exercise_id)

    if replacement.id not in {ex.id for ex in session.exercises}:
        session.exercises.append(replacement)

    await store.update(session)
    await memory.record(
        MemoryEvent(
            type=MemoryEventType.SWAP_APPLIED,
            session_id=session.id,
            payload={
                "from": exercise_id,
                "to": replacement_id,
                "occurrences": occurrences,
            },
        )
    )
    logger.info(
        "Session %s: swapped %s → %s (%d occurrence(s))",
        session.id,
        exercise_id,
        replacement_id,
        occurrences,
    )
    return session.plan


def _replace_in_plan(
    plan: WorkoutPlan, old_id: str, replacement: Exercise
) -> int:
    """Point every planned slot for ``old_id`` at ``replacement``; return count."""
    n = 0
    for day in plan.days:
        for pe in day.exercises:
            if pe.exercise_id == old_id:
                pe.exercise_id = replacement.id
                pe.name = replacement.name
                n += 1
    return n
