"""
Mobile Touch Operations - Tap, Swipe.
"""

import subprocess
import time
from typing import Optional

from langchain_core.tools import tool

from .screenshot import get_current_device, capture_mobile_screenshot

ADB_EXE = "adb"


@tool
def mobile_tap(x: int, y: int) -> str:
    """
    Tap at specific pixel coordinates on the mobile screen.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
    
    Returns:
        Confirmation of the tap.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
        return f"Tapped at ({x}, {y})"
    except Exception as e:
        return f"Tap error: {e}"


@tool
def mobile_double_tap(x: int, y: int) -> str:
    """
    Double tap at specific pixel coordinates.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
    
    Returns:
        Confirmation of the double tap.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
        time.sleep(0.1)
        subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
        return f"Double-tapped at ({x}, {y})"
    except Exception as e:
        return f"Double tap error: {e}"


@tool
def mobile_long_press(x: int, y: int, duration_ms: int = 1000) -> str:
    """
    Long press at specific coordinates.
    
    Args:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        duration_ms: Duration of the press in milliseconds.
    
    Returns:
        Confirmation of the long press.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(
            f"{ADB_EXE} {prefix}shell input swipe {x} {y} {x} {y} {duration_ms}",
            shell=True, check=True
        )
        return f"Long-pressed at ({x}, {y}) for {duration_ms}ms"
    except Exception as e:
        return f"Long press error: {e}"


@tool
def mobile_swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> str:
    """
    Swipe from one point to another.
    
    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration_ms: Duration of the swipe in milliseconds.
    
    Returns:
        Confirmation of the swipe.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(
            f"{ADB_EXE} {prefix}shell input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}",
            shell=True, check=True
        )
        return f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})"
    except Exception as e:
        return f"Swipe error: {e}"


@tool
def mobile_swipe_direction(direction: str = "up") -> str:
    """
    Swipe in a direction on the mobile screen.
    
    Args:
        direction: Direction to swipe - 'up', 'down', 'left', or 'right'.
    
    Returns:
        Confirmation of the swipe.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        # Get screen size for swipe coordinates
        _, _, size, _ = capture_mobile_screenshot(max_dim=512)
        w, h = size
        cx, cy = w // 2, h // 2
        
        swipes = {
            "up": (cx, int(h * 0.7), cx, int(h * 0.3)),
            "down": (cx, int(h * 0.3), cx, int(h * 0.7)),
            "left": (int(w * 0.8), cy, int(w * 0.2), cy),
            "right": (int(w * 0.2), cy, int(w * 0.8), cy),
        }
        
        coords = swipes.get(direction.lower(), swipes["up"])
        x1, y1, x2, y2 = coords
        
        subprocess.run(
            f"{ADB_EXE} {prefix}shell input swipe {x1} {y1} {x2} {y2} 300",
            shell=True, check=True
        )
        return f"Swiped {direction}"
    except Exception as e:
        return f"Swipe error: {e}"
