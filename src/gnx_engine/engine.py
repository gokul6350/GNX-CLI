import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.filesystem import ls
from src.tools.file_ops import read_file, write_file, edit_file
from src.tools.search import glob, grep
from src.tools.system import capture_screen
from src.tools.todos import write_todos, read_todos, mark_complete
from src.tools.web_search import web_search, web_search_detailed, fetch_url

class GNXEngine:
    def __init__(self, model_name="gemma-3-27b-it", api_key=None):
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        self.tools = [
            ls, read_file, write_file, edit_file, 
            glob, grep, capture_screen,
            write_todos, read_todos, mark_complete,
            web_search, web_search_detailed, fetch_url
        ]
        
        # Initialize Gemma directly WITHOUT DeepAgents
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
        )
        
        # Wrap with ReActAdapter for tool handling
        from src.gnx_engine.adapters import ReActAdapter
        self.agent = ReActAdapter(self.llm)
        self.agent.bind_tools(self.tools)
        
        self.chat_history = []

    def run(self, user_input: str) -> str:
        try:
            # Build message list
            messages = list(self.chat_history)
            messages.append(HumanMessage(content=user_input))
            
            # Invoke wrapped adapter (handles ReAct loop internally)
            response = self.agent.invoke(messages)
            
            # Update history with both user and assistant messages
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response.content))
            
            return response.content
        except Exception as e:
            return f"Error executing agent: {e}"
