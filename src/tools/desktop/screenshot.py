"""
Desktop Screenshot Capture.
"""

import base64
import io
import json
import os
from typing import Dict, Optional, Tuple

from mss import mss
from PIL import Image
from langchain_core.tools import tool

from src.vision_client import log_step


def capture_desktop_screenshot(
    region: Optional[Dict[str, int]] = None, 
    max_dim: Optional[int] = None
) -> Tuple[str, str, Tuple[int, int], Tuple[int, int]]:
    """
    Capture desktop screenshot.
    
    Returns:
        Tuple of (base64_data_url, file_path, (width, height), (original_width, original_height))
    """
    step_start = log_step("Capture Screenshot")
    with mss() as sct:
        mon = region or sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        original_size = img.size

        # Optionally downscale to control payload size
        if max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        
        # Save to buffer for base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        
        # Save to file (resized if max_dim is set)
        path = os.path.join(os.getcwd(), "desktop_screenshot.png")
        img.save(path)

        log_step("Capture Screenshot", step_start)
        return data_url, path, (img.width, img.height), original_size


@tool
def computer_screenshot() -> str:
    """
    Capture a screenshot of the desktop for computer control.
    Returns the path to the saved screenshot and screen dimensions.
    Use this to see the current state of the desktop before giving instructions.
    """
    try:
        # Downscale to 512x512 specifically for LLM context control
        data_url, path, size, _ = capture_desktop_screenshot(max_dim=512)
        payload = {
            "type": "screenshot",
            "path": path,
            "width": size[0],
            "height": size[1],
            # Include the data URL (already 512x512) so the main model can "see" the image
            "data_url": data_url,
            "note": "Use desktop tools or activate_vision_agent to execute actions based on what you see."
        }
        return json.dumps(payload)
    except Exception as e:
        return f"Error capturing screenshot: {e}"
