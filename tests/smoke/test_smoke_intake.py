"""Smoke: Intake Agent in isolation (was scripts/smoke_intake.py)."""

import json

import pytest
import railtracks as rt

from tests.support import FIXTURES_DIR
from gym_pt.agents import Intake_Agent
from gym_pt.models import UserProfile

pytestmark = pytest.mark.smoke


def test_intake_agent_extracts_profile():
    prompt = json.loads((FIXTURES_DIR / "sample_prompt.json").read_text())["text"]
    flow = rt.Flow(name="Intake Agent", entry_point=Intake_Agent)

    result = flow.invoke(prompt)
    profile = result.structured

    assert isinstance(profile, UserProfile)
    # The fixture prompt asks for a 3-day beginner plan with machines/dumbbells
    assert profile.days_per_week == 3
    assert profile.level.value == "beginner"
    assert profile.equipment
