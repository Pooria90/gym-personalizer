"""Exercise catalog access for the Railtracks retrieval backend.

The free-exercise-db dataset is the source of truth. Chunks stored in the
vector store carry only an ``exercise_id`` in metadata; full ``Exercise``
objects are reconstructed from the catalog loaded here, which guarantees every
retrieved id exists in the dataset (the same invariant the planner validation
in e2e.py relies on).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path

from railtracks.retrieval import Document, DocumentType
from railtracks.retrieval.loaders.base import BaseDocumentLoader

from gym_pt.config import PROJECT_ROOT
from gym_pt.models.exercise import Exercise

DEFAULT_CATALOG_PATH = PROJECT_ROOT / "free-exercise-db" / "dist" / "exercises.json"


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> dict[str, Exercise]:
    """Load the exercise dataset into an id → Exercise lookup."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {ex["id"]: Exercise.model_validate(ex) for ex in raw}


def exercise_embedding_text(exercise: Exercise) -> str:
    """Deterministic text embedded per exercise.

    Mirrors the vocabulary of the Query Agent's semantic queries (movement
    type, level, equipment, muscles) so query and document embeddings live in
    the same space. Must stay stable: changing it invalidates content hashes
    and re-embeds the whole catalog on the next ingest.
    """
    descriptors = [f"{exercise.category} exercise", f"{exercise.level} level"]
    if exercise.mechanic:
        descriptors.append(exercise.mechanic)
    if exercise.force:
        descriptors.append(f"{exercise.force} movement")
    descriptors.append(f"equipment: {exercise.equipment or 'none'}")

    parts = [f"{exercise.name}. " + ", ".join(descriptors) + "."]
    if exercise.primaryMuscles:
        parts.append("Primary muscles: " + ", ".join(exercise.primaryMuscles) + ".")
    if exercise.secondaryMuscles:
        parts.append("Secondary muscles: " + ", ".join(exercise.secondaryMuscles) + ".")
    if exercise.instructions:
        parts.append(" ".join(exercise.instructions))
    return "\n".join(parts)


class ExerciseCatalogLoader(BaseDocumentLoader):
    """Stream the exercise dataset as one ``Document`` per exercise.

    Not ``JSONLoader``: that gives every object in an array file the same
    ``source`` (the file path), and document ids derive from ``source`` — so
    each exercise would upsert-delete the previous one's chunks. A unique
    per-exercise ``source`` keeps document ids stable *and* distinct, which is
    also what makes re-ingest skip unchanged exercises via content hash.
    """

    def __init__(self, path: Path = DEFAULT_CATALOG_PATH, *, limit: int | None = None):
        self._path = path
        self._limit = limit

    async def astream(self) -> AsyncGenerator[Document, None]:
        raw = await asyncio.to_thread(
            lambda: json.loads(self._path.read_text(encoding="utf-8"))
        )
        for entry in raw[: self._limit]:
            exercise = Exercise.model_validate(entry)
            metadata = {
                "exercise_id": exercise.id,
                "level": exercise.level,
                "category": exercise.category,
            }
            if exercise.equipment:
                metadata["equipment"] = exercise.equipment
            yield Document(
                content=exercise_embedding_text(exercise),
                type=DocumentType.JSON,
                source=f"{self._path}#{exercise.id}",
                metadata=metadata,
            )
