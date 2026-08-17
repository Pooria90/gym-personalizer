"""Shared service verbs: the operations both the CLI and the API call.

No HTTP here. Stores are passed in (dependency injection) so the caller owns
persistence lifecycle: the CLI builds snapshot-backed stores per run; the API
will reuse singletons built at startup.
"""

from __future__ import annotations

import logging

from gym_pt.agents import swap_exercise
from gym_pt.models import Exercise, PlannedExercise, WorkoutPlan
from gym_pt.service.errors import (
    ExerciseNotInSession,
    InvalidReplacement,
    NoPendingRecommendations,
    SessionNotFound,
    SlotNotFound,
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
    ids/counts; not the full plan, which already lives on the session.
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


def _find_slot(session: Session, slot_id: str) -> PlannedExercise:
    """Return the one planned exercise carrying ``slot_id``."""
    for day in session.plan.days:
        for planned in day.exercises:
            if planned.slot_id == slot_id:
                return planned
    raise SlotNotFound(session.id, slot_id)


async def get_plan(session_id: str, *, store: SessionStore) -> WorkoutPlan:
    """Return the current plan for a session. Raises `SessionNotFound`."""
    session = await _require_session(session_id, store)
    return session.plan


async def recommend_swaps(
    session_id: str,
    slot_id: str,
    *,
    store: SessionStore,
) -> list[Exercise]:
    """Suggest replacements for one planned slot; does not change the plan.

    The candidates are stashed on the session so `apply_swap` can honor the
    user's pick without a second retrieval call — which means this *does*
    persist the session, even though the plan itself is untouched. Calling it
    again for the same slot replaces the stashed set.

    Raises `SessionNotFound` / `SlotNotFound`.
    """
    session = await _require_session(session_id, store)
    slot = _find_slot(session, slot_id)
    target = _find_in_pool(session, slot.exercise_id)

    candidates = await swap_exercise(target, session.profile)
    session.pending_swaps[slot_id] = candidates
    await store.update(session)

    logger.debug(
        "Session %s slot %s (%s): %d candidate(s)",
        session.id,
        slot_id,
        slot.exercise_id,
        len(candidates),
    )
    return candidates


async def apply_swap(
    session_id: str,
    slot_id: str,
    replacement_id: str,
    *,
    store: SessionStore,
    memory: Memory,
) -> WorkoutPlan:
    """Replace the exercise in one planned slot with a chosen recommendation.

    Scoped to that single occurrence — the same exercise on another day is left
    alone — and the prescription (sets/reps) carries over, since only the
    movement changes. Adds the replacement to the session pool so the plan stays
    valid, persists the session, and records a `SWAP_APPLIED` event. Does **not**
    re-run intake or the planner.

    ``replacement_id`` must come from this slot's pending recommendations, so
    `recommend_swaps` has to run first. Re-applying a swap that already landed
    is a no-op, which keeps HTTP retries safe.

    Raises `SessionNotFound` / `SlotNotFound` / `NoPendingRecommendations` /
    `InvalidReplacement`.
    """
    session = await _require_session(session_id, store)
    slot = _find_slot(session, slot_id)

    if slot.exercise_id == replacement_id:
        # Already applied: a retried request, not a new swap. Raising here
        # would fail an operation that actually succeeded.
        return session.plan

    candidates = session.pending_swaps.get(slot_id)
    if not candidates:
        raise NoPendingRecommendations(session.id, slot_id)
    replacement = next((c for c in candidates if c.id == replacement_id), None)
    if replacement is None:
        raise InvalidReplacement(slot_id, replacement_id)

    previous_id = slot.exercise_id
    slot.exercise_id = replacement.id
    slot.name = replacement.name

    if replacement.id not in {ex.id for ex in session.exercises}:
        session.exercises.append(replacement)
    # Stale now that the slot holds a different movement.
    session.pending_swaps.pop(slot_id, None)

    await store.update(session)
    await memory.record(
        MemoryEvent(
            type=MemoryEventType.SWAP_APPLIED,
            session_id=session.id,
            payload={
                "slot_id": slot_id,
                "from": previous_id,
                "to": replacement.id,
            },
        )
    )
    logger.info(
        "Session %s: slot %s swapped %s → %s",
        session.id,
        slot_id,
        previous_id,
        replacement.id,
    )
    return session.plan
