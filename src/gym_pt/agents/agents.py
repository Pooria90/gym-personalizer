import railtracks as rt

from gym_pt.models import UserProfile
from .messages import INTAKE_SYSTEM_MESSAGE


Intake_agent = rt.agent_node(
    name = "Intake Agent",
    llm = rt.llm.AnthropicLLM("claude-sonnet-4-6"),
    system_message = INTAKE_SYSTEM_MESSAGE,
    output_schema = UserProfile
)