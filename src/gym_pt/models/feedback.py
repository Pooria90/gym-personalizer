from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FeedbackAction(BaseModel):
    action: Literal["swap_exercise", "re_plan", "done"]
    exercise_id: str | None = Field(
        default=None,
        description="For swap_exercise: exact ID of the exercise to replace (copied from the plan)",
    )
    swap_query: str | None = Field(
        default=None,
        description="For swap_exercise: search query to find a replacement exercise",
    )
    updated_notes: str | None = Field(
        default=None,
        description="For re_plan: additional constraints or notes to pass to the planner",
    )
    reply: str = Field(
        ...,
        description="Brief, friendly message explaining to the user what will happen next",
    )
