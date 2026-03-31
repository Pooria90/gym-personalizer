import json
import railtracks as rt

from gym_pt.agents import Intake_Agent
from rich import print

rt.enable_logging()

flow = rt.Flow(name="Intake Agent", entry_point=Intake_Agent)

if __name__ == "__main__":
    fixture_path = "fixtures/sample_prompt.json"
    with open(fixture_path, "r") as f:
        prompt_json = json.load(f)
        prompt = prompt_json["text"]

    result = flow.invoke(prompt)
    print(result)
