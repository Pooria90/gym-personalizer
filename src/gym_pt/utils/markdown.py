from gym_pt.models import WorkoutPlan


def render_plan_markdown(plan: WorkoutPlan) -> str:
    """Render a WorkoutPlan as a Markdown string suitable for the chat UI."""
    lines: list[str] = [f"## {plan.title or 'Your Workout Plan'}"]

    if plan.notes:
        lines += [f"*{plan.notes}*", ""]

    for day in plan.days:
        header = f"### Day {day.day_index + 1}"
        if day.focus:
            header += f" — {day.focus}"
        lines.append(header)

        for ex in day.exercises:
            detail = f"**{ex.name}**"
            if ex.sets and ex.reps:
                detail += f" — {ex.sets} × {ex.reps}"
            detail += f" `{ex.exercise_id}`"
            lines.append(f"- {detail}")

        lines.append("")

    return "\n".join(lines)
