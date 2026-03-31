from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FitnessLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GoalType(str, Enum):
    CARDIO = "cardio"
    OLYMPIC_WEIGHTLIFTING = "olympic weightlifting"
    PLYOMETRICS = "plyometrics"
    POWERLIFTING = "powerlifting"
    STRENGTH = "strength"
    STRETCHING = "stretching"
    STRONGMAN = "strongman"


class UserProfile(BaseModel):
    """Inputs collected before generating a plan (agent intake)."""

    goal: GoalType = Field(
        ..., description="e.g. strength, hypertrophy, general fitness"
    )
    days_per_week: int = Field(..., ge=1, le=7)
    equipment: list[str] = Field(default_factory=list)
    level: FitnessLevel = FitnessLevel.INTERMEDIATE
    notes: str | None = Field(
        default=None,
        description="Injuries, preferences, or constraints in free text",
    )


class ExerciseQueries(BaseModel):
    """Search queries aligned with the structure of a training session."""

    warmup_query: str = Field(
        ...,
        description="Cardio or light movement to elevate heart rate before training",
        json_schema_extra={"top_k": 4},
    )
    primary_query: str = Field(
        ...,
        description="Main compound movements aligned with the user's goal and target muscles",
        json_schema_extra={"top_k": 5},
    )
    secondary_query: str = Field(
        ...,
        description="Accessory or isolation work supporting the primary movements",
        json_schema_extra={"top_k": 6},
    )
    equipment_query: str = Field(
        ...,
        description="Exercises filtered to the user's available equipment and fitness level",
        json_schema_extra={"top_k": 3},
    )
    cooldown_query: str = Field(
        ...,
        description="Stretching or static holds for recovery and flexibility",
        json_schema_extra={"top_k": 3},
    )


class PlannedExercise(BaseModel):
    exercise_id: str
    name: str
    sets: int | None = None
    reps: str | None = None


class WorkoutDay(BaseModel):
    day_index: int
    focus: str | None = None
    exercises: list[PlannedExercise] = Field(default_factory=list)


class WorkoutPlan(BaseModel):
    title: str | None = None
    days: list[WorkoutDay] = Field(default_factory=list)
    notes: str | None = None
