"""
MCP Client Manager for GNX CLI

Manages connections to multiple MCP servers and provides unified access to their tools.
Supports both stdio and HTTP transports.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConnection:
    """Represents a connection to an MCP server"""
    name: str
    transport: str  # "stdio" or "http"
    session: Optional[ClientSession] = None
    tools: List[Any] = field(default_factory=list)
    connected: bool = False
    
    # stdio transport params
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    
    # http transport params
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class MCPClientManager:
    """
    Manages connections to multiple MCP servers.
    
    Usage:
        manager = MCPClientManager()
        manager.add_server("math", transport="stdio", command="python", args=["math_server.py"])
        manager.add_server("weather", transport="http", url="http://localhost:8000/mcp")
        
        async with manager:
            tools = await manager.get_all_tools()
            # Use tools with GNX engine
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self._contexts: List[Any] = []
        self._running = False
    
    def add_server(
        self,
        name: str,
        transport: str = "stdio",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Add an MCP server configuration.
        
        Args:
            name: Unique identifier for this server
            transport: Either "stdio" or "http"
            command: Command to run for stdio transport (e.g., "python", "node")
            args: Arguments for the command (e.g., ["server.py"])
            env: Environment variables for the server process
            url: URL for http transport (e.g., "http://localhost:8000/mcp")
            headers: HTTP headers for http transport
        """
        if name in self.servers:
            logger.warning(f"Server '{name}' already exists, replacing...")
        
        self.servers[name] = MCPServerConnection(
            name=name,
            transport=transport,
            command=command,
            args=args,
            env=env,
            url=url,
            headers=headers,
        )
        logger.info(f"Added MCP server config: {name} ({transport})")
    
    def remove_server(self, name: str) -> bool:
        """Remove an MCP server configuration."""
        if name in self.servers:
            del self.servers[name]
            logger.info(f"Removed MCP server: {name}")
            return True
        return False
    
    def list_servers(self) -> List[str]:
        """List all configured server names."""
        return list(self.servers.keys())
    
    async def connect_server(self, name: str) -> bool:
        """
        Connect to a specific MCP server.
        
        Args:
            name: Name of the server to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if name not in self.servers:
            logger.error(f"Server '{name}' not found")
            return False
        
        server = self.servers[name]
        
        try:
            if server.transport == "stdio":
                return await self._connect_stdio(server)
            elif server.transport in ("http", "streamable_http", "streamable-http"):
                return await self._connect_http(server)
            else:
                logger.error(f"Unknown transport: {server.transport}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to {name}: {e}")
            return False
    
    async def _connect_stdio(self, server: MCPServerConnection) -> bool:
        """Connect to an MCP server using stdio transport."""
        if not server.command:
            logger.error(f"No command specified for stdio server {server.name}")
            return False
        
        server_params = StdioServerParameters(
            command=server.command,
            args=server.args or [],
            env=server.env,
        )
        
        # Create and store the context
        stdio_ctx = stdio_client(server_params)
        read, write = await stdio_ctx.__aenter__()
        self._contexts.append(stdio_ctx)
        
        # Create session
        session_ctx = ClientSession(read, write)
        server.session = await session_ctx.__aenter__()
        self._contexts.append(session_ctx)
        
        # Initialize
        await server.session.initialize()
        
        # Load tools
        tools_result = await server.session.list_tools()
        server.tools = tools_result.tools
        server.connected = True
        
        logger.info(f"Connected to {server.name} via stdio, loaded {len(server.tools)} tools")
        return True
    
    async def _connect_http(self, server: MCPServerConnection) -> bool:
        """Connect to an MCP server using HTTP transport."""
        if not server.url:
            logger.error(f"No URL specified for HTTP server {server.name}")
            return False
        
        try:
            from mcp.client.streamable_http import streamable_http_client
        except ImportError:
            logger.error("streamable_http_client not available, install mcp with http support")
            return False
        
        # Create HTTP client context
        http_ctx = streamable_http_client(server.url)
        read, write, _ = await http_ctx.__aenter__()
        self._contexts.append(http_ctx)
        
        # Create session
        session_ctx = ClientSession(read, write)
        server.session = await session_ctx.__aenter__()
        self._contexts.append(session_ctx)
        
        # Initialize
        await server.session.initialize()
        
        # Load tools
        tools_result = await server.session.list_tools()
        server.tools = tools_result.tools
        server.connected = True
        
        logger.info(f"Connected to {server.name} via HTTP, loaded {len(server.tools)} tools")
        return True
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect to all configured MCP servers.
        
        Returns:
            Dict mapping server names to connection success status
        """
        results = {}
        for name in self.servers:
            results[name] = await self.connect_server(name)
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers and clean up resources."""
        # Close contexts in reverse order
        for ctx in reversed(self._contexts):
            try:
                await ctx.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
        
        self._contexts.clear()
        
        for server in self.servers.values():
            server.session = None
            server.connected = False
            server.tools = []
        
        logger.info("Disconnected from all MCP servers")
    
    async def get_tools(self, server_name: str) -> List[Any]:
        """Get tools from a specific connected server."""
        if server_name not in self.servers:
            return []
        
        server = self.servers[server_name]
        if not server.connected:
            logger.warning(f"Server {server_name} not connected")
            return []
        
        return server.tools
    
    async def get_all_tools(self) -> List[Any]:
        """Get tools from all connected servers."""
        all_tools = []
        for server in self.servers.values():
            if server.connected:
                all_tools.extend(server.tools)
        return all_tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on a specific server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool result
        """
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not found")
        
        server = self.servers[server_name]
        if not server.connected or not server.session:
            raise ConnectionError(f"Server '{server_name}' not connected")
        
        result = await server.session.call_tool(tool_name, arguments)
        return result
    
    def find_server_for_tool(self, tool_name: str) -> Optional[str]:
        """Find which server provides a specific tool."""
        for server in self.servers.values():
            if server.connected:
                for tool in server.tools:
                    if tool.name == tool_name:
                        return server.name
        return None
    
    async def __aenter__(self):
        """Async context manager entry - connects to all servers."""
        await self.connect_all()
        self._running = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnects from all servers."""
        self._running = False
        await self.disconnect_all()
        return False


# Singleton instance for easy access
_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    """Get the global MCP client manager instance."""
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager


def reset_mcp_manager() -> None:
    """Reset the global MCP client manager."""
    global _manager
    _manager = None
