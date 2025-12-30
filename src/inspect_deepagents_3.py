import deepagents
import inspect

print("--- create_deep_agent signature ---")
try:
    sig = inspect.signature(deepagents.create_deep_agent)
    print("Signature parameters:")
    for name, param in sig.parameters.items():
        print(f"  {name}: {param.default} (Annotation: {param.annotation})")
except Exception as e:
    print(f"Error getting signature: {e}")

print("\n--- deepagents.backends ---")
try:
    print(dir(deepagents.backends))
except Exception as e:
    print(f"Error inspecting backends: {e}")
