"""
MCP Tool Wrapper for GNX CLI

Converts MCP tools to LangChain-compatible tools that can be used with the GNX engine.
"""

import asyncio
import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, create_model

from .client import MCPClientManager, get_mcp_manager

logger = logging.getLogger(__name__)


def _json_schema_to_pydantic_field(name: str, schema: Dict[str, Any], required: bool = False):
    """Convert JSON schema property to Pydantic field."""
    json_type = schema.get("type", "string")
    description = schema.get("description", "")
    default = schema.get("default", ... if required else None)
    
    # Map JSON types to Python types
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    python_type = type_map.get(json_type, str)
    
    if not required and default is ...:
        python_type = Optional[python_type]
        default = None
    
    return (python_type, Field(default=default, description=description))


def _create_args_schema(tool_name: str, input_schema: Dict[str, Any]) -> Type[BaseModel]:
    """Create a Pydantic model from MCP tool input schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    
    fields = {}
    for prop_name, prop_schema in properties.items():
        is_required = prop_name in required
        fields[prop_name] = _json_schema_to_pydantic_field(prop_name, prop_schema, is_required)
    
    # Create dynamic model
    model_name = f"{tool_name.replace('-', '_').replace('.', '_').title()}Args"
    return create_model(model_name, **fields)


class MCPToolWrapper(BaseTool):
    """
    Wrapper that converts an MCP tool to a LangChain tool.
    
    This allows MCP tools to be used seamlessly with the GNX engine's
    ReAct adapter and tool execution system.
    """
    name: str = ""
    description: str = ""
    server_name: str = ""
    mcp_tool_name: str = ""
    manager: Optional[MCPClientManager] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        mcp_tool: Any,
        server_name: str,
        manager: Optional[MCPClientManager] = None,
        **kwargs
    ):
        # Extract tool info
        tool_name = mcp_tool.name
        tool_desc = mcp_tool.description or f"MCP tool: {tool_name}"
        input_schema = mcp_tool.inputSchema or {"type": "object", "properties": {}}
        
        # Create args schema
        args_schema = _create_args_schema(tool_name, input_schema)
        
        super().__init__(
            name=tool_name,
            description=tool_desc,
            args_schema=args_schema,
            server_name=server_name,
            mcp_tool_name=tool_name,
            manager=manager or get_mcp_manager(),
            **kwargs
        )
    
    def _run(self, **kwargs) -> str:
        """Synchronous run - wraps async call."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop in thread if current is running
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(**kwargs))
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(**kwargs))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """Asynchronous run - calls the MCP tool."""
        if not self.manager:
            return f"Error: No MCP manager available for tool {self.name}"
        
        try:
            result = await self.manager.call_tool(
                self.server_name,
                self.mcp_tool_name,
                kwargs
            )
            
            # Parse result content
            if hasattr(result, "content"):
                content_parts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        content_parts.append(content.text)
                    elif hasattr(content, "data"):
                        content_parts.append(f"[Binary data: {len(content.data)} bytes]")
                    else:
                        content_parts.append(str(content))
                return "\n".join(content_parts) if content_parts else "Tool executed successfully"
            
            return str(result)
        
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.name}: {e}")
            return f"Error executing MCP tool {self.name}: {e}"


def create_mcp_langchain_tool(
    mcp_tool: Any,
    server_name: str,
    manager: Optional[MCPClientManager] = None
) -> BaseTool:
    """
    Create a LangChain tool from an MCP tool.
    
    Args:
        mcp_tool: The MCP tool object from session.list_tools()
        server_name: Name of the MCP server providing this tool
        manager: MCPClientManager instance (uses global if not provided)
        
    Returns:
        A LangChain BaseTool that wraps the MCP tool
    """
    return MCPToolWrapper(mcp_tool, server_name, manager)


async def load_mcp_tools_as_langchain(
    manager: Optional[MCPClientManager] = None,
    server_name: Optional[str] = None,
    prefix_with_server: bool = False
) -> List[BaseTool]:
    """
    Load MCP tools as LangChain tools.
    
    Args:
        manager: MCPClientManager instance (uses global if not provided)
        server_name: If provided, only load tools from this server
        prefix_with_server: If True, prefix tool names with server name
        
    Returns:
        List of LangChain tools
    """
    if manager is None:
        manager = get_mcp_manager()
    
    langchain_tools = []
    
    if server_name:
        # Load from specific server
        servers_to_load = [server_name] if server_name in manager.servers else []
    else:
        # Load from all servers
        servers_to_load = list(manager.servers.keys())
    
    for srv_name in servers_to_load:
        server = manager.servers.get(srv_name)
        if not server or not server.connected:
            logger.warning(f"Server {srv_name} not connected, skipping")
            continue
        
        for mcp_tool in server.tools:
            try:
                lc_tool = create_mcp_langchain_tool(mcp_tool, srv_name, manager)
                
                # Optionally prefix with server name
                if prefix_with_server:
                    lc_tool.name = f"{srv_name}_{lc_tool.name}"
                
                langchain_tools.append(lc_tool)
                logger.debug(f"Loaded MCP tool: {lc_tool.name} from {srv_name}")
            
            except Exception as e:
                logger.error(f"Error creating LangChain tool for {mcp_tool.name}: {e}")
    
    logger.info(f"Loaded {len(langchain_tools)} MCP tools as LangChain tools")
    return langchain_tools


def load_mcp_tools_sync(
    manager: Optional[MCPClientManager] = None,
    server_name: Optional[str] = None,
    prefix_with_server: bool = False
) -> List[BaseTool]:
    """
    Synchronous version of load_mcp_tools_as_langchain.
    
    Useful when you need to load tools outside of an async context.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't run async from running loop synchronously
            logger.warning("Event loop already running, returning empty list. Use async version.")
            return []
        return loop.run_until_complete(
            load_mcp_tools_as_langchain(manager, server_name, prefix_with_server)
        )
    except RuntimeError:
        return asyncio.run(
            load_mcp_tools_as_langchain(manager, server_name, prefix_with_server)
        )
