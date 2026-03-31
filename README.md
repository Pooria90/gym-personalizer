# gym-pt

An AI-powered personal trainer built on [Railtracks](https://railtracks.org) and
[Railengine](https://railengine.ai) by [Railtown AI](https://railtown.ai).

## Overview

`gym-pt` is a pipeline that takes a user's fitness profile and returns a
structured workout plan. It uses Railengine for semantic exercise retrieval
and Railtracks to orchestrate a three-stage agent pipeline.

## Pipeline
```
Intake Agent → Query Agent → Planner Agent
```

**Intake** — Collects the user's goal, fitness level, available equipment,
training days, and optional notes. Outputs a structured `UserProfile`.

**Query** — Builds five targeted semantic search queries from the profile,
fans them out in parallel against the Railengine exercise database, and
returns a deduplicated pool of relevant exercises.

**Planner** — Selects exercises from the pool and arranges them into a
structured `WorkoutPlan` with one `WorkoutDay` per training day.

<!---
## Project Structure
```
src/gym_pt/
├── agents/
│   ├── intake_agent.py
│   ├── query_agent.py
│   ├── planner_agent.py
│   └── tools.py
├── models/
│   ├── exercise.py
│   └── plan.py
├── railengine/
│   ├── retrieval.py
│   ├── query_protocol.py
│   └── sdk_patch.py
└── config.py
tests/
└── fixtures/
    ├── user_profile_beginner_strength.json
    └── exercise_queries_beginner_strength.json
```

## Setup
```bash
pip install railtracks railengine
cp .env.example .env  # add ANTHROPIC_API_KEY and RAILENGINE credentials
```

## Running
```python
from gym_pt.agents import flow

result = flow.invoke(
    "I am a beginner, 3 days a week, goal is strength. "
    "I have dumbbells and machines available."
)
print(result)
```

## Tech Stack

- **Railtracks** — agent orchestration and tool calling
- **Railengine** — vector search over the exercise database (873 exercises)
- **Anthropic Claude** — LLM backend for all three agents
- **Pydantic v2** — structured I/O between pipeline stages
--->