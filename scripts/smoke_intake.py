import railtracks as rt
from gym_pt.agents import Intake_agent
from rich import print

rt.enable_logging()

flow = rt.Flow(name="Intake Agent", entry_point=Intake_agent)

if __name__ == "__main__":
    result = flow.invoke(
        "Give me a beginner strength gym plan for 3 exercises per week using machines and dumbells."
    )
    print(result)

