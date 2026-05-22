"""Smoke test for the FollowUp Agent.

Tests all three action paths (done / swap_exercise / re_plan) using the
sample_plan.json fixture so no retrieval calls are made.

Run from the gym/ root:
    uv run python scripts/smoke_followup.py
"""

import json
import sys
from pathlib import Path

import railtracks as rt
from rich import print

from gym_pt.agents import FollowUp_Agent
from gym_pt.models import FeedbackAction

rt.enable_logging()

flow = rt.Flow(name="FollowUp Agent Smoke", entry_point=FollowUp_Agent)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_plan.json"

CASES = [
    {
        "label": "done — user is satisfied",
        "feedback": "Looks great, I'll go with this!",
        "expected_action": "done",
    },
    {
        "label": "swap_exercise — user dislikes one exercise",
        "feedback": "I don't like the Walking Treadmill on Day 1, can you replace it with something else?",
        "expected_action": "swap_exercise",
    },
    {
        "label": "re_plan — user wants structural change",
        "feedback": "I want to avoid chest exercises entirely and focus more on legs.",
        "expected_action": "re_plan",
    },
]


def run_case(plan: dict, case: dict) -> bool:
    label = case["label"]
    print(f"\n[bold cyan]── {label}[/bold cyan]")

    payload = {"plan": plan, "feedback": case["feedback"]}
    result = flow.invoke(str(payload))
    action: FeedbackAction = result.structured

    print(f"  action        : [bold]{action.action}[/bold]")
    print(f"  reply         : {action.reply}")
    if action.exercise_id:
        print(f"  exercise_id   : {action.exercise_id}")
    if action.swap_query:
        print(f"  swap_query    : {action.swap_query}")
    if action.updated_notes:
        print(f"  updated_notes : {action.updated_notes}")

    ok = action.action == case["expected_action"]
    status = "[bold green]PASS[/bold green]" if ok else "[bold red]FAIL[/bold red]"
    print(f"  result        : {status} (expected {case['expected_action']!r}, got {action.action!r})")
    return ok


if __name__ == "__main__":
    with open(FIXTURE) as f:
        plan = json.load(f)

    results = [run_case(plan, case) for case in CASES]

    passed = sum(results)
    total = len(results)
    print(f"\n[bold]{'='*40}[/bold]")
    print(f"[bold]Results: {passed}/{total} passed[/bold]")

    if passed < total:
        sys.exit(1)
