"""
Mobile Use Tool for GNX CLI
Mobile automation using V_action vision model via ADB.

Workflow:
1. GNX Engine (main model) receives user goal and views screenshot
2. GNX Engine instructs V_action with natural language
3. V_action views screenshot and returns precise coordinates
4. Action is executed on mobile device via ADB
"""

import base64
import json
import io
import os
import subprocess
import time
from typing import Optional, Tuple, List

from PIL import Image
from langchain_core.tools import tool
from dotenv import load_dotenv

from src.gnx_engine.vl_provider import query_vl_model, to_pixels, ActionResult, log_step

# Ensure .env is loaded and OVERRIDES any existing env vars
load_dotenv(override=True)

ADB_EXE = "adb"  # Assumes ADB is in PATH


def _adb_command(cmd: str, device_id: Optional[str] = None) -> str:
    """Execute an ADB command."""
    prefix = f"-s {device_id} " if device_id else ""
    full_cmd = f"{ADB_EXE} {prefix}{cmd}"
    
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ADB Error: {e.stderr}"


def _capture_mobile_screenshot(device_id: Optional[str] = None, max_dim: Optional[int] = None) -> Tuple[str, str, Tuple[int, int], Tuple[int, int]]:
    """
    Capture screenshot from mobile device via ADB.
    
    Returns:
        Tuple of (base64_data_url, file_path, (width, height), (original_width, original_height))
    """
    step_start = log_step("Capture Mobile Screenshot")
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


def _v_action_mobile(instruction: str, screenshot_data_url: str, screen_size: Tuple[int, int], history: List[str] = None) -> ActionResult:
    """
    Call V_action vision model for mobile actions.
    
    Args:
        instruction: Natural language instruction (from GNX engine)
        screenshot_data_url: Base64 encoded screenshot
        screen_size: Screen dimensions (width, height)
        history: List of previous actions and results
    
    Returns:
        ActionResult with action type and coordinates
    """
    system_prompt = (
        "You are V_action, a vision-based action executor for mobile phone automation. "
        "You are working as an agent to complete a multi-step goal.\n"
        "Given a goal, screen history, and current phone screenshot, determine the exact NEXT action to perform.\n\n"
        "Return ONLY valid JSON with these fields:\n"
        "- action: one of 'tap', 'double_tap', 'long_press', 'type', 'swipe', 'swipe_up', 'swipe_down', 'back', 'home', 'wait', 'terminate'\n"
        "- coordinate: [x, y] in 1000x1000 normalized grid (0-1000)\n"
        "- coordinate2: [x, y] for swipe end point (only for swipe action)\n"
        "- text: text to type (only for type action)\n"
        "- description: brief description of the element (e.g., 'red button', 'search bar')\n"
        "- time: milliseconds to wait or long press duration\n"
        "- status: completion message (only for terminate action)\n\n"
        "CRITICAL RULES:\n"
        "1. If the target element is NOT visible, do NOT guess coordinates. Instead, output a 'swipe_up' or 'swipe_down' action to look for it.\n"
        "2. If you have searched and the element is definitely not found, return: {\"action\": \"terminate\", \"status\": \"Element not found\"}\n"
        "3. If the goal is achieved, return: {\"action\": \"terminate\", \"status\": \"Goal completed\"}\n\n"
        "Examples:\n"
        '{\"action\": \"tap\", \"coordinate\": [500, 500], \"description\": \"Settings icon\"}\n'
        '{\"action\": \"type\", \"coordinate\": [500, 300], \"text\": \"hello\", \"description\": \"Search bar\"}\n'
        '{\"action\": \"swipe\", \"coordinate\": [500, 800], \"coordinate2\": [500, 200]}\n'
        '{\"action\": \"swipe_up\", \"coordinate\": [500, 500]}\n'
        '{\"action\": \"back\"}\n'
        '{\"action\": \"home\"}\n'
        '{\"action\": \"terminate\", \"status\": \"Task completed successfully\"}\n\n'
        "Important: Mobile coordinates start from top-left. Status bar is at the top."
    )
    
    history_text = "\n".join(history) if history else "None"
    user_text = (
        f"Goal: {instruction}\n"
        f"Screen size: {screen_size[0]}x{screen_size[1]}\n"
        f"History of actions:\n{history_text}\n\n"
        "What is the next step?"
    )

    return query_vl_model(system_prompt, user_text, screenshot_data_url)


def _execute_mobile_action(act: ActionResult, screen_size: Tuple[int, int], device_id: Optional[str] = None) -> str:
    """Execute action on mobile device via ADB."""
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        if act.action == "tap" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            return f"Tapped at ({x}, {y})"
        
        elif act.action == "double_tap" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            time.sleep(0.1)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            return f"Double-tapped at ({x}, {y})"
        
        elif act.action == "long_press" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            duration = act.time or 1000  # Default 1 second
            subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y} {x} {y} {int(duration)}", shell=True, check=True)
            return f"Long-pressed at ({x}, {y}) for {duration}ms"
        
        elif act.action == "type":
            if act.coordinate:
                x, y = to_pixels(act.coordinate, screen_size)
                subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
                time.sleep(0.3)
            if act.text:
                # Escape spaces for ADB
                escaped_text = act.text.replace(" ", "%s").replace("'", "\\'")
                subprocess.run(f'{ADB_EXE} {prefix}shell input text "{escaped_text}"', shell=True, check=True)
                return f"Typed: '{act.text}'"
            return "Type action but no text provided"
        
        elif act.action == "swipe" and act.coordinate and act.coordinate2:
            x1, y1 = to_pixels(act.coordinate, screen_size)
            x2, y2 = to_pixels(act.coordinate2, screen_size)
            duration = act.time or 300
            subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x1} {y1} {x2} {y2} {int(duration)}", shell=True, check=True)
            return f"Swiped from ({x1}, {y1}) to ({x2}, {y2})"
        
        elif act.action == "swipe_up":
            x = screen_size[0] // 2
            y1 = int(screen_size[1] * 0.7)
            y2 = int(screen_size[1] * 0.3)
            subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y1} {x} {y2} 300", shell=True, check=True)
            return "Swiped up"
        
        elif act.action == "swipe_down":
            x = screen_size[0] // 2
            y1 = int(screen_size[1] * 0.3)
            y2 = int(screen_size[1] * 0.7)
            subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y1} {x} {y2} 300", shell=True, check=True)
            return "Swiped down"
        
        elif act.action == "back":
            subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_BACK", shell=True, check=True)
            return "Pressed back button"
        
        elif act.action == "home":
            subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_HOME", shell=True, check=True)
            return "Pressed home button"
        
        elif act.action == "wait":
            wait_time = (act.time or 1000) / 1000.0 if act.time and act.time > 5 else (act.time or 1.0)
            time.sleep(float(wait_time))
            return f"Waited {wait_time} seconds"
        
        elif act.action == "terminate":
            return f"Task completed: {act.status or 'Done'}"
        
        elif act.action == "error":
            return f"Error: {act.status}"
        
        else:
            return f"Unknown action: {act.action}"
    
    except Exception as e:
        return f"Execution error: {e}"


# Store device ID for session
_current_device_id: Optional[str] = None


# ============================================================================
# LangChain Tools for GNX Engine
# ============================================================================

@tool
def mobile_devices() -> str:
    """
    List connected Android devices via ADB.
    Use this to check which devices are available for mobile control.
    
    Returns:
        List of connected device IDs
    """
    try:
        result = subprocess.run(
            f"{ADB_EXE} devices",
            shell=True,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        lines = output.split("\n")[1:]  # Skip header
        devices = [line.split("\t")[0] for line in lines if "\t" in line and "device" in line]
        
        if devices:
            return f"Connected devices:\n" + "\n".join(f"- {d}" for d in devices)
        else:
            return "No devices connected. Make sure USB debugging is enabled and device is connected."
    except Exception as e:
        return f"Error listing devices: {e}"


@tool
def mobile_connect(device_id: str = "") -> str:
    """
    Connect to a specific Android device for mobile control.
    If device_id is empty, uses the first available device.
    
    Args:
        device_id: The device ID to connect to (optional)
    
    Returns:
        Connection status
    """
    global _current_device_id
    
    try:
        if device_id:
            _current_device_id = device_id
            return f"Connected to device: {device_id}"
        else:
            # Get first available device
            result = subprocess.run(
                f"{ADB_EXE} devices",
                shell=True,
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split("\n")[1:]
            devices = [line.split("\t")[0] for line in lines if "\t" in line and "device" in line]
            
            if devices:
                _current_device_id = devices[0]
                return f"Connected to device: {_current_device_id}"
            else:
                return "No devices available. Please connect a device first."
    except Exception as e:
        return f"Connection error: {e}"


@tool
def mobile_screenshot() -> str:
    """
    Capture a screenshot from the connected mobile device.
    Returns the path to the saved screenshot and screen dimensions.
    Use this to see the current state of the phone before giving instructions.
    """
    global _current_device_id
    
    try:
        # Downscale to 512x512 for LLM context
        data_url, path, size, _ = _capture_mobile_screenshot(_current_device_id, max_dim=512)
        
        # Return JSON payload compatible with NativeToolAdapter
        payload = {
            "type": "screenshot",
            "path": path,
            "width": size[0],
            "height": size[1],
            "data_url": data_url,
            "note": "Use mobile_control to execute actions based on what you see."
        }
        return json.dumps(payload)
    except Exception as e:
        return f"Error capturing screenshot: {e}\nMake sure a device is connected (use mobile_devices to check)."


@tool
def mobile_control(instruction: str) -> str:
    """
    Execute a mobile control instruction using vision-based AI.
    
    The instruction should describe what UI element to interact with, for example:
    - "Tap on the Settings app"
    - "Tap on the search bar"
    - "Type 'hello' in the text field"
    - "Swipe up to scroll"
    - "Press the back button"
    
    Args:
        instruction: Natural language description of the action to perform
    
    Returns:
        Result of the action execution
    """
    global _current_device_id
    total_start = log_step(f"Mobile Control: {instruction[:50]}...")
    
    try:
        # Try to parse JSON instruction
        try:
            instr_json = json.loads(instruction)
            if isinstance(instr_json, dict):
                # Format structured instruction for vision model
                formatted_instr = (
                    f"Action: {instr_json.get('action', 'unknown')}\n"
                    f"Target: {instr_json.get('target', 'unknown')}\n"
                    f"Location: {instr_json.get('location', 'unknown')}\n"
                    f"Description: {instr_json.get('description', '')}"
                )
                instruction = formatted_instr
        except json.JSONDecodeError:
            pass  # Use raw instruction if not JSON

        history = []
        max_steps = 15
        
        for step in range(max_steps):
            step_start = log_step(f"Step {step+1}")
            
            # Capture current screen state
            # Resize to 512x512 to prevent timeouts with large payloads
            data_url, path, screen_size, original_size = _capture_mobile_screenshot(_current_device_id, max_dim=512)
            
            # Get action from V_action model
            action_result = _v_action_mobile(instruction, data_url, screen_size, history)
            
            if action_result.action == "error":
                log_step("Mobile Control (Error)", total_start)
                return f"V_action error: {action_result.status}"
            
            # Execute the action
            exec_start = log_step(f"Executing Action: {action_result.action}")
            result = _execute_mobile_action(action_result, original_size, _current_device_id)
            log_step("Action Execution", exec_start)
            
            # Record history
            step_desc = f"Step {step+1}: Action={action_result.action}, Desc={action_result.description}, Result={result}"
            history.append(step_desc)
            
            log_step(f"Step {step+1}", step_start)
            
            # Check termination
            if action_result.action == "terminate":
                log_step("Mobile Control", total_start)
                return f"Finished: {action_result.status}\nHistory:\n" + "\n".join(history)
            
            # Wait a bit for UI to settle
            time.sleep(1.0)
            
        log_step("Mobile Control (Max Steps)", total_start)
        return f"Max steps ({max_steps}) reached. History:\n" + "\n".join(history)
    
    except Exception as e:
        log_step("Mobile Control (Exception)", total_start)
        return f"Mobile control error: {e}"


@tool
def mobile_tap(x: int, y: int) -> str:
    """
    Tap at specific pixel coordinates on the mobile screen.
    Use this when you know the exact coordinates.
    
    Args:
        x: X coordinate in pixels
        y: Y coordinate in pixels
    
    Returns:
        Confirmation of the tap
    """
    global _current_device_id
    prefix = f"-s {_current_device_id} " if _current_device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
        return f"Tapped at ({x}, {y})"
    except Exception as e:
        return f"Tap error: {e}"


@tool
def mobile_type_text(text: str) -> str:
    """
    Type text on the mobile device (assumes keyboard is open).
    
    Args:
        text: The text to type
    
    Returns:
        Confirmation of the typed text
    """
    global _current_device_id
    prefix = f"-s {_current_device_id} " if _current_device_id else ""
    
    try:
        escaped_text = text.replace(" ", "%s").replace("'", "\\'")
        subprocess.run(f'{ADB_EXE} {prefix}shell input text "{escaped_text}"', shell=True, check=True)
        return f"Typed: '{text}'"
    except Exception as e:
        return f"Type error: {e}"


@tool
def mobile_swipe(direction: str = "up") -> str:
    """
    Swipe in a direction on the mobile screen.
    
    Args:
        direction: Direction to swipe - 'up', 'down', 'left', or 'right'
    
    Returns:
        Confirmation of the swipe
    """
    global _current_device_id
    prefix = f"-s {_current_device_id} " if _current_device_id else ""
    
    try:
        # Get screen size for swipe coordinates
        data_url, path, size, _ = _capture_mobile_screenshot(_current_device_id, max_dim=512)
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
        
        subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x1} {y1} {x2} {y2} 300", shell=True, check=True)
        return f"Swiped {direction}"
    except Exception as e:
        return f"Swipe error: {e}"


@tool
def mobile_button(button: str) -> str:
    """
    Press a system button on the mobile device.
    
    Args:
        button: Button to press - 'back', 'home', 'recent', 'power', 'volume_up', 'volume_down'
    
    Returns:
        Confirmation of the button press
    """
    global _current_device_id
    prefix = f"-s {_current_device_id} " if _current_device_id else ""
    
    button_map = {
        "back": "KEYCODE_BACK",
        "home": "KEYCODE_HOME",
        "recent": "KEYCODE_APP_SWITCH",
        "power": "KEYCODE_POWER",
        "volume_up": "KEYCODE_VOLUME_UP",
        "volume_down": "KEYCODE_VOLUME_DOWN",
        "enter": "KEYCODE_ENTER",
    }
    
    try:
        keycode = button_map.get(button.lower())
        if not keycode:
            return f"Unknown button: {button}. Available: {', '.join(button_map.keys())}"
        
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent {keycode}", shell=True, check=True)
        return f"Pressed {button} button"
    except Exception as e:
        return f"Button error: {e}"


# Export all tools
MOBILE_USE_TOOLS = [
    mobile_devices,
    mobile_connect,
    mobile_screenshot,
    mobile_control,
    mobile_tap,
    mobile_type_text,
    mobile_swipe,
    mobile_button,
]
