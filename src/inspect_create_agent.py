
import langchain.agents
import inspect

try:
    print("Signature of langchain.agents.create_agent:")
    print(inspect.signature(langchain.agents.create_agent))
except Exception as e:
    print(e)
