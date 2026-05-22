import logging
from typing import cast

import railtracks as rt
from railtracks.human_in_the_loop import ChatUI, HILMessage

from gym_pt.agents import (
    FollowUp_Agent,
    Intake_Agent,
    Planner_Agent,
    query_and_retrieve,
    retrieve_exercises,
)
from gym_pt.models import Exercise, PlannedExercise, UserProfile, WorkoutPlan
from gym_pt.utils.markdown import render_plan_markdown

logger = logging.getLogger(__name__)

_FIELDS_FOR_PLANNER = ["id", "equipment", "primaryMuscles", "secondaryMuscles", "category"]


def _filter_for_planner(exercises: list[Exercise]) -> list[dict]:
    return [{k: getattr(ex, k) for k in _FIELDS_FOR_PLANNER} for ex in exercises]


def _swap_exercise_in_plan(
    plan: WorkoutPlan, old_id: str, new_ex: Exercise
) -> WorkoutPlan:
    for day in plan.days:
        for i, ex in enumerate(day.exercises):
            if ex.exercise_id == old_id:
                day.exercises[i] = PlannedExercise(
                    exercise_id=new_ex.id,
                    name=new_ex.name,
                    sets=ex.sets,
                    reps=ex.reps,
                )
                return plan
    return plan


@rt.function_node
async def chat_main():
    chat_ui = ChatUI(port=8000, auto_open=True)
    await chat_ui.connect()

    try:
        await chat_ui.send_message(
            HILMessage(content="**Welcome to GymPT!** What kind of workout are you looking for?")
        )

        # ── Stage 1: Intake ──────────────────────────────────────────────────
        user_msg = await chat_ui.receive_message()
        if not user_msg:
            return

        await chat_ui.send_message(HILMessage(content="*Analysing your request...*"))
        intake_output = await rt.call(Intake_Agent, user_msg.content)
        profile: UserProfile = intake_output.structured

        # ── Stage 2: Retrieval ───────────────────────────────────────────────
        await chat_ui.send_message(
            HILMessage(
                content=f"*Searching exercises for **{profile.goal}** training ({profile.level}, {profile.days_per_week} days/week)...*"
            )
        )
        exercises: list[Exercise] = cast(
            list,
            await rt.call(rt.function_node(query_and_retrieve), profile),
        )
        logger.debug("Retrieved %d exercises", len(exercises))

        # ── Stage 3: Planning ────────────────────────────────────────────────
        await chat_ui.send_message(
            HILMessage(content=f"*Found {len(exercises)} exercises. Building your plan...*")
        )
        plan_output = await rt.call(
            Planner_Agent,
            str({"profile": profile, "exercises": _filter_for_planner(exercises)}),
        )
        plan: WorkoutPlan = plan_output.structured

        await chat_ui.send_message(HILMessage(content=render_plan_markdown(plan)))
        await chat_ui.send_message(
            HILMessage(
                content="How does this look? Ask me to replace any exercise, adjust the plan, or say **done** when you're happy."
            )
        )

        # ── Feedback loop ────────────────────────────────────────────────────
        while True:
            feedback_msg = await chat_ui.receive_message()
            if not feedback_msg:
                break

            action_output = await rt.call(
                FollowUp_Agent,
                str({"plan": plan.model_dump(), "feedback": feedback_msg.content}),
            )
            action = action_output.structured

            await chat_ui.send_message(HILMessage(content=action.reply))

            if action.action == "done":
                break

            elif action.action == "swap_exercise":
                if not action.exercise_id or not action.swap_query:
                    await chat_ui.send_message(
                        HILMessage(content="*Could not identify which exercise to swap — can you be more specific?*")
                    )
                    continue

                alternatives = await retrieve_exercises(action.swap_query, top_k=5)
                current_ids = {
                    ex.exercise_id for day in plan.days for ex in day.exercises
                }
                replacement = next(
                    (ex for ex in (alternatives or []) if ex.id not in current_ids),
                    None,
                )
                if replacement:
                    plan = _swap_exercise_in_plan(plan, action.exercise_id, replacement)
                    await chat_ui.send_message(HILMessage(content=render_plan_markdown(plan)))
                else:
                    await chat_ui.send_message(
                        HILMessage(
                            content="*Couldn't find a suitable replacement — try describing what you're looking for differently.*"
                        )
                    )

            elif action.action == "re_plan":
                notes_parts = [p for p in [profile.notes, action.updated_notes] if p]
                updated_notes = " ".join(notes_parts) or None
                profile = profile.model_copy(update={"notes": updated_notes})
                await chat_ui.send_message(HILMessage(content="*Rebuilding your plan...*"))
                plan_output = await rt.call(
                    Planner_Agent,
                    str({"profile": profile, "exercises": _filter_for_planner(exercises)}),
                )
                plan = plan_output.structured
                await chat_ui.send_message(HILMessage(content=render_plan_markdown(plan)))

    finally:
        await chat_ui.disconnect()


flow = rt.Flow("GymPT Chat", entry_point=chat_main)

if __name__ == "__main__":
    flow.invoke()
