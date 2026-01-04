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
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

from openai import OpenAI
from PIL import Image
from langchain_core.tools import tool
from dotenv import load_dotenv

# Ensure .env is loaded and OVERRIDES any existing env vars
load_dotenv(override=True)

# Configuration
HF_BASE_URL = "https://router.huggingface.co/v1"
V_ACTION_MODEL = "Qwen/Qwen3-VL-8B-Instruct:fastest"  # Vision-Language model for actions

ADB_EXE = "adb"  # Assumes ADB is in PATH


@dataclass
class ActionResult:
    """Result from V_action model"""
    action: str
    coordinate: Optional[Tuple[int, int]] = None
    coordinate2: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None
    raw: Optional[str] = None


def _get_client() -> OpenAI:
    """Get OpenAI client for HuggingFace router."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError(
            "HF_TOKEN not found in environment. "
            "Please set HF_TOKEN in your .env file for V_action vision model. "
            "Get a valid token from: https://huggingface.co/settings/tokens"
        )
    # Verify token is not a placeholder
    if token.startswith("your_") or len(token) < 10:
        raise ValueError(
            f"Invalid HF_TOKEN: '{token}'. "
            "Please update HF_TOKEN in your .env file with a valid token from https://huggingface.co/settings/tokens"
        )
    
    # Debug: Show what token is being used (masked)
    masked_token = token[:10] + "..." + token[-5:] if len(token) > 15 else "***"
    print(f"[DEBUG] Using HF_TOKEN: {masked_token}")
    
    return OpenAI(base_url=HF_BASE_URL, api_key=token)


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


def _capture_mobile_screenshot(device_id: Optional[str] = None) -> Tuple[str, str, Tuple[int, int]]:
    """
    Capture screenshot from mobile device via ADB.
    
    Returns:
        Tuple of (base64_data_url, file_path, (width, height))
    """
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
    w, h = img.size
    
    with open(local_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    
    data_url = f"data:image/png;base64,{b64}"
    
    return data_url, local_path, (w, h)


def _v_action_mobile(instruction: str, screenshot_data_url: str, screen_size: Tuple[int, int]) -> ActionResult:
    """
    Call V_action vision model for mobile actions.
    
    Args:
        instruction: Natural language instruction (from GNX engine)
        screenshot_data_url: Base64 encoded screenshot
        screen_size: Screen dimensions (width, height)
    
    Returns:
        ActionResult with action type and coordinates
    """
    system_prompt = (
        "You are V_action, a vision-based action executor for mobile phone automation. "
        "Given an instruction and phone screenshot, determine the exact action to perform.\n\n"
        "Return ONLY valid JSON with these fields:\n"
        "- action: one of 'tap', 'double_tap', 'long_press', 'type', 'swipe', 'swipe_up', 'swipe_down', 'back', 'home', 'wait', 'terminate'\n"
        "- coordinate: [x, y] in 1000x1000 normalized grid (0-1000)\n"
        "- coordinate2: [x, y] for swipe end point (only for swipe action)\n"
        "- text: text to type (only for type action)\n"
        "- description: brief description of the element (e.g., 'red button', 'search bar')\n"
        "- time: milliseconds to wait or long press duration\n"
        "- status: completion message (only for terminate action)\n\n"
        "CRITICAL RULES:\n"
        "1. If the target element is NOT visible, do NOT guess coordinates.\n"
        "2. If the element is definitely not found, return: {\"action\": \"terminate\", \"status\": \"Element not found\"}\n\n"
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
    
    try:
        resp = _get_client().chat.completions.create(
            model=V_ACTION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Instruction: {instruction}\nScreen size: {screen_size[0]}x{screen_size[1]}"},
                        {"type": "image_url", "image_url": {"url": screenshot_data_url}},
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content
        act = _parse_action_json(raw)
        act.raw = raw
        return act
    except Exception as e:
        error_msg = str(e)
        # Better error messages for auth failures
        if "401" in error_msg or "Invalid username" in error_msg or "Unauthorized" in error_msg:
            error_msg = (
                f"HuggingFace authentication failed. Error: {error_msg}\n"
                f"Your HF_TOKEN in .env may be invalid or expired.\n"
                f"Get a new token from: https://huggingface.co/settings/tokens\n"
                f"Make sure the token has 'read' permissions."
            )
        return ActionResult(action="error", status=error_msg, raw=str(e))


def _parse_action_json(content: str) -> ActionResult:
    """Parse JSON response from V_action model."""
    start = content.find("{")
    end = content.rfind("}")
    
    if start != -1 and end != -1:
        try:
            obj = json.loads(content[start:end + 1])
            c1 = obj.get("coordinate")
            c2 = obj.get("coordinate2")
            return ActionResult(
                action=obj.get("action", "unknown"),
                coordinate=tuple(c1) if c1 else None,
                coordinate2=tuple(c2) if c2 else None,
                text=obj.get("text"),
                time=obj.get("time"),
                status=obj.get("status"),
                description=obj.get("description"),
            )
        except json.JSONDecodeError:
            pass
    
    # Fallback parsing
    try:
        data = {}
        parts = content.split(", ")
        for part in parts:
            if ": " in part:
                key, val = part.split(": ", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith("[") and val.endswith("]"):
                    val = json.loads(val)
                elif val.isdigit():
                    val = int(val)
                elif val.replace(".", "", 1).isdigit():
                    val = float(val)
                elif val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                data[key] = val
        
        c1 = data.get("coordinate")
        c2 = data.get("coordinate2")
        return ActionResult(
            action=data.get("action", "unknown"),
            coordinate=tuple(c1) if c1 else None,
            coordinate2=tuple(c2) if c2 else None,
            text=data.get("text"),
            time=data.get("time"),
            status=data.get("status"),
            description=data.get("description"),
        )
    except Exception:
        return ActionResult(action="error", status=f"Failed to parse: {content}")


def _to_pixels(coord: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
    """Convert normalized coordinates (0-1000) to screen pixels."""
    x, y = coord
    if x > 1 or y > 1:
        px = int(x / 1000.0 * screen_size[0])
        py = int(y / 1000.0 * screen_size[1])
    else:
        px = int(x * screen_size[0])
        py = int(y * screen_size[1])
    return max(0, px), max(0, py)


def _execute_mobile_action(act: ActionResult, screen_size: Tuple[int, int], device_id: Optional[str] = None) -> str:
    """Execute action on mobile device via ADB."""
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        if act.action == "tap" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            return f"Tapped at ({x}, {y})"
        
        elif act.action == "double_tap" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            time.sleep(0.1)
            subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
            return f"Double-tapped at ({x}, {y})"
        
        elif act.action == "long_press" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            duration = act.time or 1000  # Default 1 second
            subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y} {x} {y} {int(duration)}", shell=True, check=True)
            return f"Long-pressed at ({x}, {y}) for {duration}ms"
        
        elif act.action == "type":
            if act.coordinate:
                x, y = _to_pixels(act.coordinate, screen_size)
                subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
                time.sleep(0.3)
            if act.text:
                # Escape spaces for ADB
                escaped_text = act.text.replace(" ", "%s").replace("'", "\\'")
                subprocess.run(f'{ADB_EXE} {prefix}shell input text "{escaped_text}"', shell=True, check=True)
                return f"Typed: '{act.text}'"
            return "Type action but no text provided"
        
        elif act.action == "swipe" and act.coordinate and act.coordinate2:
            x1, y1 = _to_pixels(act.coordinate, screen_size)
            x2, y2 = _to_pixels(act.coordinate2, screen_size)
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
        data_url, path, size = _capture_mobile_screenshot(_current_device_id)
        
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

        # Capture current screen state
        data_url, path, screen_size = _capture_mobile_screenshot(_current_device_id)
        
        # Get action from V_action model
        action_result = _v_action_mobile(instruction, data_url, screen_size)
        
        if action_result.action == "error":
            return f"V_action error: {action_result.status}"
        
        # Execute the action
        result = _execute_mobile_action(action_result, screen_size, _current_device_id)
        
        # Build response
        response = f"Instruction: {instruction}\n"
        response += f"Action: {action_result.action}\n"
        if action_result.description:
            response += f"Description: {action_result.description}\n"
        if action_result.coordinate:
            px, py = _to_pixels(action_result.coordinate, screen_size)
            response += f"Coordinate: ({px}, {py})\n"
        response += f"Result: {result}"
        
        return response
    
    except Exception as e:
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
        data_url, path, size = _capture_mobile_screenshot(_current_device_id)
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
