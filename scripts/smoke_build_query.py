import json
import railtracks as rt

from gym_pt.agents import Query_Agent
from rich import print

rt.enable_logging()

flow = rt.Flow(name="Query Agent", entry_point=Query_Agent)

if __name__ == "__main__":
    fixture_path = "fixtures/sample_profile.json"
    with open(fixture_path, "r") as f:
        profile = json.load(f)

    result = flow.invoke(str(profile))
    print(result)
