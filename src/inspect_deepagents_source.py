import deepagents
import inspect

try:
    print(inspect.getsource(deepagents.create_deep_agent))
except Exception as e:
    print(f"Error getting source: {e}")
