import deepagents
import inspect

print("--- create_deep_agent help ---")
help(deepagents.create_deep_agent)

print("\n--- create_deep_agent signature ---")
try:
    print(inspect.signature(deepagents.create_deep_agent))
except Exception as e:
    print(e)
