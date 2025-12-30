try:
    from langchain.agents import AgentExecutor
    print("AgentExecutor: OK")
except ImportError as e:
    print(f"AgentExecutor: Fail ({e})")

try:
    from langchain.agents import create_tool_calling_agent
    print("create_tool_calling_agent: OK")
except ImportError as e:
    print(f"create_tool_calling_agent: Fail ({e})")

import langchain
print(f"LangChain version: {langchain.__version__}")
