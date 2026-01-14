"""
Desktop Tools Package - Atomic desktop automation tools.
"""

from .screenshot import computer_screenshot, capture_desktop_screenshot
from .mouse import desktop_click, desktop_scroll, desktop_drag, desktop_move
from .keyboard import desktop_type, desktop_type_unicode, desktop_hotkey, desktop_press

# All desktop tools for registration
DESKTOP_TOOLS = [
    computer_screenshot,
    desktop_click,
    desktop_scroll,
    desktop_drag,
    desktop_move,
    desktop_type,
    desktop_type_unicode,
    desktop_hotkey,
    desktop_press,
]

__all__ = [
    "computer_screenshot",
    "capture_desktop_screenshot",
    "desktop_click",
    "desktop_scroll",
    "desktop_drag",
    "desktop_move",
    "desktop_type",
    "desktop_type_unicode",
    "desktop_hotkey",
    "desktop_press",
    "DESKTOP_TOOLS",
]
