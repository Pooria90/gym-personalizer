"""Shared service verbs — the operations both the CLI and the API call.

No HTTP here. Stores are passed in (dependency injection) so the caller owns
persistence lifecycle: the CLI builds snapshot-backed stores per run; the API
will reuse singletons built at startup.
"""

from __future__ import annotations

import logging

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
