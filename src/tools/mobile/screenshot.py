"""
Mobile Screenshot Capture via ADB.
"""

import base64
import io
import json
import os
import subprocess
from typing import Optional, Tuple

from PIL import Image
from langchain_core.tools import tool

from src.vision_client import log_step

ADB_EXE = "adb"  # Assumes ADB is in PATH

# Store device ID for session
_current_device_id: Optional[str] = None


def get_current_device() -> Optional[str]:
    """Get the current connected device ID."""
    return _current_device_id


def set_current_device(device_id: Optional[str]) -> None:
    """Set the current device ID."""
    global _current_device_id
    _current_device_id = device_id


def capture_mobile_screenshot(
    device_id: Optional[str] = None, 
    max_dim: Optional[int] = None
) -> Tuple[str, str, Tuple[int, int], Tuple[int, int]]:
    """
    Capture screenshot from mobile device via ADB.
    
    Returns:
        Tuple of (base64_data_url, file_path, (width, height), (original_width, original_height))
    """
    step_start = log_step("Capture Mobile Screenshot")
    device_id = device_id or _current_device_id
    prefix = f"-s {device_id} " if device_id else ""
    remote_path = "/sdcard/gnx_screenshot.png"
    local_path = os.path.join(os.getcwd(), "mobile_screenshot.png")
    
    # Properly quote paths with spaces
    quoted_local_path = f'"{local_path}"'
    
    # Capture screenshot on device
    subprocess.run(
        f'{ADB_EXE} {prefix}shell screencap -p {remote_path}',
        shell=True,
        check=True,
        capture_output=True,
        text=True
    )
    
    # Pull screenshot to local machine (with quoted path)
    subprocess.run(
        f'{ADB_EXE} {prefix}pull {remote_path} {quoted_local_path}',
        shell=True,
        check=True,
        capture_output=True,
        text=True
    )
    
    # Clean up remote file
    subprocess.run(
        f'{ADB_EXE} {prefix}shell rm {remote_path}',
        shell=True,
        check=True,
        capture_output=True,
        text=True
    )
    
    # Get image dimensions and create base64
    img = Image.open(local_path)
    original_size = img.size
    
    # Resize if max_dim is provided
    if max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        
    # Save to buffer for base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    
    data_url = f"data:image/png;base64,{b64}"
    
    log_step("Capture Mobile Screenshot", step_start)
    return data_url, local_path, (img.width, img.height), original_size


@tool
def mobile_screenshot() -> str:
    """
    Capture a screenshot from the connected mobile device.
    Returns the path to the saved screenshot and screen dimensions.
    Use this to see the current state of the phone before giving instructions.
    """
    try:
        # Downscale to 512x512 for LLM context
        data_url, path, size, _ = capture_mobile_screenshot(max_dim=512)
        
        # Return JSON payload compatible with NativeToolAdapter
        payload = {
            "type": "screenshot",
            "path": path,
            "width": size[0],
            "height": size[1],
            "data_url": data_url,
            "note": "Use mobile tools or activate_vision_agent to execute actions based on what you see."
        }
        return json.dumps(payload)
    except Exception as e:
        return f"Error capturing screenshot: {e}\nMake sure a device is connected (use mobile_devices to check)."
