"""
MCP Configuration Loader for GNX CLI

Loads MCP server configurations from JSON files.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default config file locations
DEFAULT_CONFIG_PATHS = [
    "mcp_servers.json",
    ".gnx/mcp_servers.json",
    os.path.expanduser("~/.gnx/mcp_servers.json"),
]


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    transport: str = "stdio"  # "stdio" or "http"
    enabled: bool = True
    
    # stdio transport params
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    
    # http transport params
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    
    # Metadata
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "MCPServerConfig":
        """Create config from dictionary."""
        return cls(
            name=name,
            transport=data.get("transport", "stdio"),
            enabled=data.get("enabled", True),
            command=data.get("command"),
            args=data.get("args"),
            env=data.get("env"),
            url=data.get("url"),
            headers=data.get("headers"),
            description=data.get("description"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "transport": self.transport,
            "enabled": self.enabled,
        }
        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        if self.url:
            result["url"] = self.url
        if self.headers:
            result["headers"] = self.headers
        if self.description:
            result["description"] = self.description
        return result


@dataclass 
class MCPConfig:
    """Full MCP configuration."""
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    
    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled server configs."""
        return [s for s in self.servers.values() if s.enabled]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mcpServers": {
                name: config.to_dict()
                for name, config in self.servers.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPConfig":
        """Create config from dictionary."""
        servers = {}
        servers_data = data.get("mcpServers", data.get("servers", {}))
        
        for name, server_data in servers_data.items():
            servers[name] = MCPServerConfig.from_dict(name, server_data)
        
        return cls(servers=servers)


def load_mcp_config(config_path: Optional[str] = None) -> MCPConfig:
    """
    Load MCP configuration from a JSON file.
    
    Args:
        config_path: Path to config file. If None, searches default locations.
        
    Returns:
        MCPConfig object
        
    The config file format follows the Claude Desktop format:
    {
        "mcpServers": {
            "server-name": {
                "transport": "stdio",
                "command": "python",
                "args": ["server.py"],
                "env": {"KEY": "value"},
                "description": "Optional description"
            },
            "http-server": {
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "headers": {"Authorization": "Bearer token"}
            }
        }
    }
    """
    # Find config file
    if config_path:
        paths_to_try = [config_path]
    else:
        paths_to_try = DEFAULT_CONFIG_PATHS
    
    for path in paths_to_try:
        if os.path.exists(path):
            logger.info(f"Loading MCP config from: {path}")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return MCPConfig.from_dict(data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                continue
    
    logger.info("No MCP config file found, returning empty config")
    return MCPConfig()


def save_mcp_config(config: MCPConfig, config_path: str = "mcp_servers.json") -> bool:
    """
    Save MCP configuration to a JSON file.
    
    Args:
        config: MCPConfig to save
        config_path: Path to save to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
        logger.info(f"Saved MCP config to: {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


def create_example_config(config_path: str = "mcp_servers.example.json") -> bool:
    """Create an example MCP configuration file."""
    example_config = {
        "mcpServers": {
            "filesystem": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
                "description": "MCP server for filesystem operations",
                "enabled": False
            },
            "github": {
                "transport": "stdio", 
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
                },
                "description": "MCP server for GitHub operations",
                "enabled": False
            },
            "weather": {
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "description": "Example HTTP MCP server",
                "enabled": False
            },
            "custom-python-server": {
                "transport": "stdio",
                "command": "python",
                "args": ["path/to/your/mcp_server.py"],
                "description": "Your custom Python MCP server",
                "enabled": False
            }
        }
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(example_config, f, indent=2)
        logger.info(f"Created example MCP config: {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating example config: {e}")
        return False
