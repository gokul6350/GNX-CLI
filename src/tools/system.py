from langchain_core.tools import tool
from PIL import ImageGrab
import os
import datetime
import time

@tool
def capture_screen(filename: str = None) -> str:
    """Capture a screenshot of the desktop."""
    try:
        screenshot = ImageGrab.grab()
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Ensure it saves in the workspace or specific folder if needed
        # For now, saves in CWD
        screenshot.save(filename)
        return f"Screenshot saved to {filename}"
    except Exception as e:
        return f"Error capturing screen: {e}"


@tool
def wait(seconds: float = 2.0) -> str:
    """
    Wait for a specified number of seconds.
    Useful to wait for UI elements to load, animations to complete, or app transitions.
    Works for both computer and mobile automation tasks.
    
    Args:
        seconds: Number of seconds to wait (default: 2.0)
    
    Returns:
        Confirmation of the wait
    """
    try:
        time.sleep(seconds)
        return f"Waited {seconds} seconds"
    except Exception as e:
        return f"Wait error: {e}"


# Export all tools
SYSTEM_TOOLS = [
    capture_screen,
    wait,
]
