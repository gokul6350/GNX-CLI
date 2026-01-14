"""
Mobile Keyboard Operations - Type text.
"""

import subprocess

from langchain_core.tools import tool

from .screenshot import get_current_device

ADB_EXE = "adb"


@tool
def mobile_type(text: str) -> str:
    """
    Type text on the mobile device (assumes keyboard is open).
    
    Args:
        text: The text to type.
    
    Returns:
        Confirmation of the typed text.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        # Escape spaces for ADB
        escaped_text = text.replace(" ", "%s").replace("'", "\\'")
        subprocess.run(
            f'{ADB_EXE} {prefix}shell input text "{escaped_text}"',
            shell=True, check=True
        )
        return f"Typed: '{text}'"
    except Exception as e:
        return f"Type error: {e}"


@tool
def mobile_keyevent(keycode: str) -> str:
    """
    Send a keyevent to the device.
    
    Args:
        keycode: Android keycode name (e.g., 'KEYCODE_ENTER', 'KEYCODE_BACK').
    
    Returns:
        Confirmation of the keyevent.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(
            f"{ADB_EXE} {prefix}shell input keyevent {keycode}",
            shell=True, check=True
        )
        return f"Sent keyevent: {keycode}"
    except Exception as e:
        return f"Keyevent error: {e}"
