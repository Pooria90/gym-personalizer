import railtracks as rt

from gym_pt.models import UserProfile, ExerciseQueries, WorkoutPlan
from .messages import (
    INTAKE_SYSTEM_MESSAGE,
    QUERY_SYSTEM_MESSAGE,
    PLANNER_SYSTEM_MESSAGE,
)


Intake_Agent = rt.agent_node(
    name="Intake Agent",
    llm=rt.llm.AnthropicLLM("claude-sonnet-4-6"),
    system_message=INTAKE_SYSTEM_MESSAGE,
    output_schema=UserProfile,
)


Query_Agent = rt.agent_node(
    name="Query Agent",
    llm=rt.llm.AnthropicLLM("claude-sonnet-4-6"),
    system_message=QUERY_SYSTEM_MESSAGE,
    output_schema=ExerciseQueries,
)


Planner_Agent = rt.agent_node(
    name="Planner Agent",
    llm=rt.llm.AnthropicLLM("claude-sonnet-4-6"),
    system_message=PLANNER_SYSTEM_MESSAGE,
    output_schema=WorkoutPlan,
)
