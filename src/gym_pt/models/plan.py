from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FitnessLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserProfile(BaseModel):
    """Inputs collected before generating a plan (agent intake)."""

    goal: str = Field(..., description="e.g. strength, hypertrophy, general fitness")
    days_per_week: int = Field(..., ge=1, le=7)
    equipment: list[str] = Field(default_factory=list)
    level: FitnessLevel = FitnessLevel.INTERMEDIATE
    notes: str | None = Field(
        default=None,
        description="Injuries, preferences, or constraints in free text",
    )


class PlannedExercise(BaseModel):
    """One slot in a workout day, referencing catalog exercises by id."""

    exercise_id: str
    name: str
    sets: int | None = None
    reps: str | None = None
    notes: str | None = None


class WorkoutDay(BaseModel):
    day_index: int = Field(..., ge=0, description="0-based day index in the microcycle")
    focus: str | None = Field(default=None, description="e.g. push, pull, legs")
    exercises: list[PlannedExercise] = Field(default_factory=list)


class WorkoutPlan(BaseModel):
    """Structured output for the plan generator / formatter (Phase 3+)."""

    title: str | None = None
    weeks: int = Field(default=1, ge=1)
    days: list[WorkoutDay] = Field(default_factory=list)
