from pydantic import BaseModel, Field


class Exercise(BaseModel):
    """Canonical exercise document aligned with Railengine vector search payloads."""

    name: str
    force: str
    level: str
    mechanic: str
    equipment: str
    primaryMuscles: list[str]
    secondaryMuscles: list[str]
    instructions: list[str]
    category: str
    images: list[str]
    id: str = Field(..., description="Stable id from the exercise catalog / engine")


# Backward-compatible name for code that followed workspace-tmp/retrieve.py
ExerciseModel = Exercise
