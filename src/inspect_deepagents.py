import deepagents
import inspect

print("--- deepagents dir ---")
for x in dir(deepagents):
    print(x)

print("\n--- deepagents content ---")
try:
    print(deepagents.__all__)
except:
    pass

# Check for specific classes
classes = [name for name, obj in inspect.getmembers(deepagents) if inspect.isclass(obj)]
print("\n--- Classes ---")
for c in classes:
    print(c)

# Check for tools
print("\n--- Submodules/Tools? ---")
help(deepagents)
