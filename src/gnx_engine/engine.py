import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.filesystem import ls
from src.tools.file_ops import read_file, write_file, edit_file
from src.tools.search import glob, grep
from src.tools.system import SYSTEM_TOOLS
from src.tools.todos import write_todos, read_todos, mark_complete
from src.tools.web_search import web_search, web_search_detailed, fetch_url
from src.tools.computer_use import COMPUTER_USE_TOOLS
from src.tools.mobile_use import MOBILE_USE_TOOLS
from src.tools.ui_automation import UI_AUTOMATION_TOOLS
from src.utils.token_counter import count_messages_tokens

class GNXEngine:
    # Free tier token limit: 15,000 tokens per minute for gemma-3-27b
    GEMMA_FREE_TIER_LIMIT = 15000
    TOKEN_RESET_INTERVAL = 60  # seconds
    
    def __init__(self, model_name="gemma-3-27b-it", api_key=None):
        self.model_name = model_name
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        # All tools including computer_use and mobile_use by default
        self.tools = [
            ls, read_file, write_file, edit_file, 
            glob, grep,
            write_todos, read_todos, mark_complete,
            web_search, web_search_detailed, fetch_url
        ]
        
        # Add system utility tools (wait, capture_screen, etc.)
        self.tools.extend(SYSTEM_TOOLS)
        
        # Add computer use tools (desktop automation)
        self.tools.extend(COMPUTER_USE_TOOLS)
        # Add UI automation helpers that work with UIA trees
        self.tools.extend(UI_AUTOMATION_TOOLS)
        
        # Add mobile use tools (phone automation via ADB)
        self.tools.extend(MOBILE_USE_TOOLS)
        
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
        self.tokens_used_this_minute = 0
        self.last_token_reset = time.time()

    def _check_token_quota(self, messages: list) -> tuple[bool, str]:
        """Check if we have token quota available. Returns (can_proceed, message)"""
        current_time = time.time()
        
        # Reset token counter if minute has passed
        if current_time - self.last_token_reset > self.TOKEN_RESET_INTERVAL:
            self.tokens_used_this_minute = 0
            self.last_token_reset = current_time
        
        # Estimate tokens for this request
        estimated_tokens = count_messages_tokens(messages)
        remaining_tokens = self.GEMMA_FREE_TIER_LIMIT - self.tokens_used_this_minute
        
        if estimated_tokens > remaining_tokens:
            wait_time = int(self.TOKEN_RESET_INTERVAL - (current_time - self.last_token_reset))
            msg = (
                f"\n❌ TOKEN QUOTA EXCEEDED (Free Tier Limit)\n"
                f"   Tokens used this minute: {self.tokens_used_this_minute}/{self.GEMMA_FREE_TIER_LIMIT}\n"
                f"   Estimated tokens for this request: {estimated_tokens}\n"
                f"   Please wait ~{wait_time} seconds for quota reset\n"
            )
            return False, msg
        
        # Warn if approaching limit
        if self.tokens_used_this_minute + estimated_tokens > self.GEMMA_FREE_TIER_LIMIT * 0.8:
            msg = (
                f"\n⚠️  WARNING: Approaching token quota\n"
                f"   Used: {self.tokens_used_this_minute} / {self.GEMMA_FREE_TIER_LIMIT}\n"
                f"   This request will use: ~{estimated_tokens} tokens\n"
            )
            return True, msg
        
        return True, ""

    def run(self, user_input: str) -> str:
        try:
            # Build message list
            messages = list(self.chat_history)
            messages.append(HumanMessage(content=user_input))
            
            # Check token quota
            can_proceed, quota_msg = self._check_token_quota(messages)
            if not can_proceed:
                return quota_msg
            
            if quota_msg:
                print(quota_msg)
            
            # Invoke wrapped adapter (handles ReAct loop internally)
            response = self.agent.invoke(messages)
            
            # Track tokens used
            self.tokens_used_this_minute += count_messages_tokens(messages)
            
            # Update history with both user and assistant messages
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response.content))
            
            return response.content
        except Exception as e:
            error_str = str(e)
            # Check for rate limit errors
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                return (
                    f"\n❌ API QUOTA EXCEEDED\n"
                    f"   You've hit the free tier token limit (15,000 tokens/minute)\n"
                    f"   Please wait ~60 seconds and try again\n"
                    f"   Error: {error_str}\n"
                )
            return f"Error executing agent: {e}"
