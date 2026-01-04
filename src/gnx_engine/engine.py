import asyncio
import logging
import os
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.gnx_engine.providers import PROVIDERS, create_llm
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
from src.utils.logger_client import history_logger

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class GNXEngine:
    # Groq free tier: 6000 tokens/min for Llama 4 Scout
    # See: https://console.groq.com/settings/limits
    FREE_TIER_TOKEN_LIMIT = 6000
    TOKEN_RESET_INTERVAL = 60  # seconds
    
    def __init__(self, provider=None, model_name=None, api_key=None, load_mcp=True, mcp_config_path=None):
        # Determine provider from args, env, or default to groq
        self.provider = provider or os.getenv("GNX_DEFAULT_PROVIDER", "groq").lower()
        
        if self.provider not in PROVIDERS:
            raise ValueError(f"Unknown provider: {self.provider}. Supported: {list(PROVIDERS.keys())}")
        
        provider_config = PROVIDERS[self.provider]
        
        # Determine model name
        if model_name:
            self.model_name = model_name
        else:
            env_model = os.getenv(f"{self.provider.upper()}_MODEL")
            self.model_name = env_model or provider_config["default_model"]
        
        # Set API key from args or environment
        if api_key:
            os.environ[provider_config["env_key"]] = api_key
        
        # Verify API key is available
        if not os.getenv(provider_config["env_key"]):
            logger.warning(f"No API key found for {self.provider}. Set {provider_config['env_key']} in .env or environment.")
        
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
        
        # MCP support
        self.mcp_manager = None
        self.mcp_tools = []
        if load_mcp:
            self._load_mcp_servers(mcp_config_path)
        
        # Initialize the LLM based on provider
        self.llm = self._create_llm()
        
        # Use NativeToolAdapter for native tool calling support
        from src.gnx_engine.adapters import NativeToolAdapter
        self.agent = NativeToolAdapter(self.llm)
        self.agent.bind_tools(self.tools)
        
        self.chat_history = []
        self.tokens_used_this_minute = 0
        self.last_token_reset = time.time()
    
    def _create_llm(self):
        """Create the LLM instance based on current provider and model."""
        return create_llm(self.provider, self.model_name)
    
    def switch_provider(self, provider: str, model_name: str = None):
        """Switch to a different provider/model at runtime."""
        provider = provider.lower()
        if provider not in PROVIDERS:
            return False, f"Unknown provider: {provider}. Supported: {list(PROVIDERS.keys())}"
        
        provider_config = PROVIDERS[provider]
        
        # Check API key
        if not os.getenv(provider_config["env_key"]):
            return False, f"No API key for {provider}. Set {provider_config['env_key']} in .env"
        
        # Update provider and model
        self.provider = provider
        self.model_name = model_name or provider_config["default_model"]
        
        # Recreate the LLM
        self.llm = self._create_llm()
        
        # Rebind tools to new adapter with native tool calling
        from src.gnx_engine.adapters import NativeToolAdapter
        self.agent = NativeToolAdapter(self.llm)
        self.agent.bind_tools(self.tools)
        
        return True, f"Switched to {provider} with model {self.model_name}"
    
    def list_models(self, provider: str = None):
        """List available models for a provider."""
        provider = provider or self.provider
        if provider not in PROVIDERS:
            return []
        return PROVIDERS[provider]["models"]
    
    def get_current_config(self):
        """Get current provider and model configuration."""
        return {
            "provider": self.provider,
            "model": self.model_name,
            "available_providers": list(PROVIDERS.keys())
        }
    
    def _load_mcp_servers(self, config_path=None):
        """Load and connect to MCP servers from config."""
        try:
            from src.mcp.config import load_mcp_config
            from src.mcp.client import MCPClientManager
            from src.mcp.tools import load_mcp_tools_as_langchain
            
            # Load config
            config = load_mcp_config(config_path)
            enabled_servers = config.get_enabled_servers()
            
            if not enabled_servers:
                logger.info("No enabled MCP servers found in config")
                return
            
            logger.info(f"Found {len(enabled_servers)} enabled MCP servers")
            
            # Create manager and add servers
            self.mcp_manager = MCPClientManager()
            for server_config in enabled_servers:
                self.mcp_manager.add_server(
                    name=server_config.name,
                    transport=server_config.transport,
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env,
                    url=server_config.url,
                    headers=server_config.headers,
                )
            
            # Connect and load tools (run in event loop)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def connect_and_load():
                results = await self.mcp_manager.connect_all()
                connected = sum(1 for v in results.values() if v)
                logger.info(f"Connected to {connected}/{len(results)} MCP servers")
                
                # Load tools
                mcp_tools = await load_mcp_tools_as_langchain(
                    self.mcp_manager,
                    prefix_with_server=True  # Prefix to avoid name collisions
                )
                return mcp_tools
            
            if loop.is_running():
                # Schedule for later if loop is running
                logger.warning("Event loop running, MCP tools will be loaded later")
            else:
                self.mcp_tools = loop.run_until_complete(connect_and_load())
                self.tools.extend(self.mcp_tools)
                logger.info(f"Added {len(self.mcp_tools)} MCP tools to engine")
        
        except ImportError as e:
            logger.warning(f"MCP support not available: {e}")
        except Exception as e:
            logger.error(f"Error loading MCP servers: {e}")
    
    def add_mcp_server(self, name, transport="stdio", **kwargs):
        """
        Add an MCP server dynamically at runtime.
        
        Args:
            name: Server name
            transport: "stdio" or "http"
            **kwargs: Server-specific params (command, args, url, etc.)
        """
        try:
            from src.mcp.client import MCPClientManager
            from src.mcp.tools import load_mcp_tools_as_langchain
            
            if self.mcp_manager is None:
                self.mcp_manager = MCPClientManager()
            
            self.mcp_manager.add_server(name, transport, **kwargs)
            
            # Connect and load tools
            async def connect_and_load():
                success = await self.mcp_manager.connect_server(name)
                if success:
                    new_tools = await load_mcp_tools_as_langchain(
                        self.mcp_manager,
                        server_name=name,
                        prefix_with_server=True
                    )
                    return new_tools
                return []
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.warning("Event loop running, cannot add MCP server synchronously")
                    return False
                new_tools = loop.run_until_complete(connect_and_load())
            except RuntimeError:
                new_tools = asyncio.run(connect_and_load())
            
            if new_tools:
                self.mcp_tools.extend(new_tools)
                self.tools.extend(new_tools)
                # Rebind tools
                self.agent.bind_tools(self.tools)
                logger.info(f"Added MCP server '{name}' with {len(new_tools)} tools")
                return True
            return False
        
        except Exception as e:
            logger.error(f"Error adding MCP server: {e}")
            return False
    
    def list_mcp_servers(self):
        """List all configured MCP servers and their status."""
        if not self.mcp_manager:
            return {}
        return {
            name: {
                "transport": server.transport,
                "connected": server.connected,
                "tools": [t.name for t in server.tools] if server.tools else []
            }
            for name, server in self.mcp_manager.servers.items()
        }
    
    def list_mcp_tools(self):
        """List all loaded MCP tools."""
        return [tool.name for tool in self.mcp_tools]

    def _check_token_quota(self, messages: list) -> tuple[bool, str]:
        """Check if we have token quota available. Returns (can_proceed, message)"""
        current_time = time.time()
        
        # Reset token counter if minute has passed
        if current_time - self.last_token_reset > self.TOKEN_RESET_INTERVAL:
            self.tokens_used_this_minute = 0
            self.last_token_reset = current_time
        
        # Estimate tokens for this request
        estimated_tokens = count_messages_tokens(messages)
        remaining_tokens = self.FREE_TIER_TOKEN_LIMIT - self.tokens_used_this_minute
        
        if estimated_tokens > remaining_tokens:
            wait_time = int(self.TOKEN_RESET_INTERVAL - (current_time - self.last_token_reset))
            msg = (
                f"\n❌ TOKEN QUOTA EXCEEDED (Free Tier Limit)\n"
                f"   Tokens used this minute: {self.tokens_used_this_minute}/{self.FREE_TIER_TOKEN_LIMIT}\n"
                f"   Estimated tokens for this request: {estimated_tokens}\n"
                f"   Please wait ~{wait_time} seconds for quota reset\n"
            )
            return False, msg
        
        # Warn if approaching limit
        if self.tokens_used_this_minute + estimated_tokens > self.FREE_TIER_TOKEN_LIMIT * 0.8:
            msg = (
                f"\n⚠️  WARNING: Approaching token quota\n"
                f"   Used: {self.tokens_used_this_minute} / {self.FREE_TIER_TOKEN_LIMIT}\n"
                f"   This request will use: ~{estimated_tokens} tokens\n"
            )
            return True, msg
        
        return True, ""

    def run(self, user_input: str) -> str:
        try:
            # Log User Input
            history_logger.log("user", user_input, is_context=True)

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
            # Returns the full conversation history including tool calls
            full_conversation = self.agent.invoke(messages)
            
            # Get the final response (last message)
            last_message = full_conversation[-1]
            final_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            # Log Final Response
            history_logger.log("ai", final_content, is_context=True)
            
            # Track tokens used
            self.tokens_used_this_minute += count_messages_tokens(full_conversation)
            
            # Update history with the full conversation state (excluding SystemMessage)
            if len(full_conversation) > 0 and isinstance(full_conversation[0], SystemMessage):
                self.chat_history = full_conversation[1:]
            else:
                self.chat_history = full_conversation
            
            return final_content
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
