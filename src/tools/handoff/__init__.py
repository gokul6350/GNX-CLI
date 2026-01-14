"""
Handoff Tools Package - Tools for delegating to sub-agents.
"""

from .vision import activate_vision_agent

HANDOFF_TOOLS = [
    activate_vision_agent,
]

__all__ = [
    "activate_vision_agent",
    "HANDOFF_TOOLS",
]
