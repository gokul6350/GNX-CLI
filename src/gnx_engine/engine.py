import os
from langchain_google_genai import ChatGoogleGenerativeAI
# Import create_deep_agent from deepagents
from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.filesystem import ls
from src.tools.file_ops import read_file, write_file, edit_file
from src.tools.search import glob, grep
from src.tools.system import capture_screen
from src.tools.todos import write_todos, read_todos, mark_complete

class GNXEngine:
    def __init__(self, model_name="gemma-3-27b-it", api_key=None):
        if api_key:
            # Check if key is just the placeholder, if so relies on user env or this demo key
            os.environ["GOOGLE_API_KEY"] = api_key
        
        # self.llm = ChatGoogleGenerativeAI(model=model_name)
        
        self.tools = [
            ls, read_file, write_file, edit_file, 
            glob, grep, capture_screen,
            write_todos, read_todos, mark_complete
        ]
        
        # Wrap LLM with ReActAdapter for Gemma 3
        from src.gnx_engine.adapters import ReActAdapter
        # Initialize Gemma WITHOUT any tool-related parameters to avoid function calling
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
        )
        wrapped_llm = ReActAdapter(self.llm)
        
        # We use create_deep_agent from DeepAgents
        self.agent = create_deep_agent(
            model=wrapped_llm,
            tools=self.tools,
        )
        
        self.chat_history = []

    def run(self, user_input: str) -> str:
        try:
            # Prepare input for StateGraph
            messages = list(self.chat_history)
            messages.append(HumanMessage(content=user_input))
            
            # invoke returns the final state
            response_state = self.agent.invoke({"messages": messages})
            
            # The 'messages' key in state has the full history including new tool calls and AI response
            output_messages = response_state["messages"]
            self.chat_history = output_messages
            
            # Get the last message (which should be the AI's final answer)
            last_msg = output_messages[-1]
            return last_msg.content
        except Exception as e:
            return f"Error executing agent: {e}"
