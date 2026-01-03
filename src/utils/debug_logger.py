"""
Advanced debug logging for GNX CLI.
Provides detailed logging when DEBUG=True in config.py
"""
import sys
import os
from datetime import datetime
from typing import Any, Optional

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from config import DEBUG
except ImportError:
    DEBUG = False


class DebugLogger:
    """Advanced debug logger with categories and formatting."""
    
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
    }
    
    CATEGORY_COLORS = {
        "TOKEN": "cyan",
        "IMAGE": "magenta",
        "TOOL": "green",
        "MODEL": "blue",
        "ERROR": "red",
        "WARN": "yellow",
        "INFO": "dim",
    }
    
    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else DEBUG
        self._indent_level = 0
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if terminal supports it."""
        if not sys.stdout.isatty():
            return text
        color_code = self.COLORS.get(color, "")
        reset = self.COLORS["reset"]
        return f"{color_code}{text}{reset}"
    
    def _format_message(self, category: str, message: str, data: Any = None) -> str:
        """Format a debug message with timestamp and category."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        indent = "  " * self._indent_level
        
        color = self.CATEGORY_COLORS.get(category, "dim")
        cat_str = self._colorize(f"[{category}]", color)
        time_str = self._colorize(f"[{timestamp}]", "dim")
        
        formatted = f"{time_str} {cat_str} {indent}{message}"
        
        if data is not None:
            if isinstance(data, dict):
                for k, v in data.items():
                    formatted += f"\n{' ' * 24}{indent}  {k}: {v}"
            else:
                formatted += f"\n{' ' * 24}{indent}  {data}"
        
        return formatted
    
    def log(self, category: str, message: str, data: Any = None):
        """Log a debug message if debug mode is enabled."""
        if not self.enabled:
            return
        print(self._format_message(category, message, data))
    
    def token(self, message: str, data: Any = None):
        """Log token-related debug info."""
        self.log("TOKEN", message, data)
    
    def image(self, message: str, data: Any = None):
        """Log image-related debug info."""
        self.log("IMAGE", message, data)
    
    def tool(self, message: str, data: Any = None):
        """Log tool-related debug info."""
        self.log("TOOL", message, data)
    
    def model(self, message: str, data: Any = None):
        """Log model-related debug info."""
        self.log("MODEL", message, data)
    
    def error(self, message: str, data: Any = None):
        """Log error (always shown regardless of debug mode)."""
        print(self._format_message("ERROR", message, data))
    
    def warn(self, message: str, data: Any = None):
        """Log warning."""
        self.log("WARN", message, data)
    
    def info(self, message: str, data: Any = None):
        """Log info."""
        self.log("INFO", message, data)
    
    def indent(self):
        """Increase indent level."""
        self._indent_level += 1
        return self
    
    def dedent(self):
        """Decrease indent level."""
        self._indent_level = max(0, self._indent_level - 1)
        return self
    
    def section(self, title: str):
        """Print a section header."""
        if not self.enabled:
            return
        line = "─" * 50
        print(f"\n{self._colorize(line, 'dim')}")
        print(f"{self._colorize('│', 'dim')} {self._colorize(title, 'bold')}")
        print(f"{self._colorize(line, 'dim')}")


# Global debug logger instance
debug = DebugLogger()


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return DEBUG
