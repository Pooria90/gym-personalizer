import railtracks as rt
import json

from rich import print
from gym_pt.agents import query_and_retrieve
from gym_pt.models import UserProfile

# rt.enable_logging()

flow = rt.Flow("Query and Retrieve", entry_point=rt.function_node(query_and_retrieve))

if __name__ == "__main__":
    with open("fixtures/sample_profile.json", "r") as f:
        profile = UserProfile.model_validate(json.load(f))

    exercises = flow.invoke(profile)

    print(f"Retrieved {len(exercises)} exercises\n")
    for ex in exercises:
        print(f"  [{ex.category}] {ex.name} | {ex.equipment} | {ex.level}")
