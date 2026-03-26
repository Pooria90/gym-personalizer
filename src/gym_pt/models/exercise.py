from pydantic import BaseModel, Field


class Exercise(BaseModel):
    name: str
    force: str | None = None
    level: str
    mechanic: str | None = None
    equipment: str | None = None
    primaryMuscles: list[str]
    secondaryMuscles: list[str]
    instructions: list[str]
    category: str
    images: list[str]
    id: str = Field(..., description="Stable id from the exercise catalog / engine")


# Backward-compatible name for code that followed workspace-tmp/retrieve.py
ExerciseModel = Exercise
