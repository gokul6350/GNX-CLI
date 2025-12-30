from langchain_core.tools import tool
from PIL import ImageGrab
import os
import datetime

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
