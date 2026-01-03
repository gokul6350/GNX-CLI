
import os
import sys

sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()  # Load from .env file

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from src.tools.filesystem import ls

def test():
    try:
        model = ChatGoogleGenerativeAI(model="gemma-3-27b-it")
        tools = [ls]
        
        # Pull the react prompt
        prompt = hub.pull("hwchase17/react")
        
        agent = create_react_agent(model, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
        
        print("Agent created. Invoking...")
        response = agent_executor.invoke({"input": "list the files in the current directory"})
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
