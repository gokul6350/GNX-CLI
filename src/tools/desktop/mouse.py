"""
Desktop Mouse Operations - Click, Drag, Scroll.
"""

import threading
import time
import tkinter as tk
from typing import Tuple

import pyautogui
from langchain_core.tools import tool

from src.vision_client import to_pixels

# Safety settings
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

HIGHLIGHT_DURATION = 1.5
HIGHLIGHT_SIZE = 100


def _show_highlight(x: int, y: int, duration: float = HIGHLIGHT_DURATION) -> None:
    """Show visual highlight circle at click location."""
    def runner():
        size = HIGHLIGHT_SIZE
        left = int(x - size / 2)
        top = int(y - size / 2)
        
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-transparentcolor", "magenta")
            root.configure(bg="magenta")
            root.geometry(f"{size}x{size}+{left}+{top}")
            
            canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="magenta")
            canvas.pack()
            canvas.create_oval(4, 4, size - 4, size - 4, fill="", outline="red", width=5)
            
            root.after(int(duration * 1000), root.destroy)
            root.mainloop()
        except Exception:
            pass  # Silently fail if display not available
    
    threading.Thread(target=runner, daemon=True).start()


@tool
def desktop_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """
    Click at specific pixel coordinates on the desktop.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        button: Mouse button - 'left', 'right', or 'middle'.
        clicks: Number of clicks (1 for single, 2 for double).
    
    Returns:
        Confirmation of the click.
    """
    try:
        _show_highlight(x, y)
        pyautogui.moveTo(x, y)
        time.sleep(0.1)
        
        if clicks == 2:
            pyautogui.doubleClick(x, y, button=button)
            return f"Double-clicked at ({x}, {y}) with {button} button"
        else:
            pyautogui.click(x, y, button=button)
            return f"Clicked at ({x}, {y}) with {button} button"
    except Exception as e:
        return f"Click error: {e}"


@tool
def desktop_scroll(x: int, y: int, direction: str = "down", amount: int = 3) -> str:
    """
    Scroll at specific coordinates.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        direction: 'up' or 'down'.
        amount: Number of scroll clicks.
    
    Returns:
        Confirmation of the scroll.
    """
    try:
        pyautogui.moveTo(x, y)
        clicks = -amount if direction.lower() == "down" else amount
        pyautogui.scroll(clicks)
        return f"Scrolled {direction} at ({x}, {y}) by {amount} clicks"
    except Exception as e:
        return f"Scroll error: {e}"


@tool
def desktop_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> str:
    """
    Drag from one point to another.
    
    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration: Duration of the drag in seconds.
    
    Returns:
        Confirmation of the drag.
    """
    try:
        _show_highlight(start_x, start_y)
        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
        return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
    except Exception as e:
        return f"Drag error: {e}"


@tool
def desktop_move(x: int, y: int) -> str:
    """
    Move mouse to specific coordinates without clicking.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
    
    Returns:
        Confirmation of the move.
    """
    try:
        pyautogui.moveTo(x, y)
        return f"Moved mouse to ({x}, {y})"
    except Exception as e:
        return f"Move error: {e}"
