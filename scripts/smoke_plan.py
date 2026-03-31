import json
import railtracks as rt

from gym_pt.agents import Planner_Agent
from rich import print

rt.enable_logging()

flow = rt.Flow(name="Planner Agent", entry_point=Planner_Agent)

if __name__ == "__main__":
    with open("fixtures/sample_profile.json", "r") as f:
        profile = json.load(f)
    
    fields_to_keep = ["id", "equipment", "primaryMuscles", "secondaryMuscles", "category"]
    with open("fixtures/sample_retrieved_exercises.json", "r") as f:
        exercises: list = json.load(f)
        filtered_exercises = [
            {k: ex.get(k) for k in fields_to_keep}
            for ex in exercises
        ]

    query = {
        "profile": profile,
        "exercises": filtered_exercises
    }
    print(query)

    result = flow.invoke(str(query))
    print(result.structured)
    
