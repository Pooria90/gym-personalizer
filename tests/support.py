"""Shared test helpers: fixture paths, model factories, and smoke-test guards."""

import importlib.util
from pathlib import Path

import pytest

from gym_pt.config import get_settings
from gym_pt.models import Exercise

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_exercise(id_: str, **overrides) -> Exercise:
    defaults = {
        "name": id_.replace("_", " "),
        "level": "beginner",
        "equipment": "dumbbell",
        "primaryMuscles": ["chest"],
        "secondaryMuscles": [],
        "instructions": ["Do the movement with control."],
        "category": "strength",
        "images": [],
        "id": id_,
    }
    defaults.update(overrides)
    return Exercise.model_validate(defaults)


def railtracks_store_ready() -> bool:
    settings = get_settings()
    return bool(settings.openai_api_key) and settings.chroma_path.exists()


def railengine_available() -> bool:
    settings = get_settings()
    has_sdk = importlib.util.find_spec("railtown") is not None
    return has_sdk and bool(settings.engine_pat) and bool(settings.engine_id)


needs_railtracks_store = pytest.mark.skipif(
    not railtracks_store_ready(),
    reason="needs OPENAI_API_KEY and a populated gym/.chroma (run scripts/ingest.py)",
)

needs_railengine = pytest.mark.skipif(
    not railengine_available(),
    reason="needs rail-engine extra (uv sync --extra railengine) and ENGINE_PAT/ENGINE_ID",
)
