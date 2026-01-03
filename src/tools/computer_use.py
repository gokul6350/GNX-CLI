"""
Computer Use Tool for GNX CLI
Desktop automation using V_action vision model.

Workflow:
1. GNX Engine (main model) receives user goal and views screenshot
2. GNX Engine instructs V_action with natural language
3. V_action views screenshot and returns precise coordinates
4. Action is executed on desktop
"""

import base64
import io
import json
import os
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import pyautogui
from mss import mss
from openai import OpenAI
from PIL import Image
from langchain_core.tools import tool

# Configuration
HF_BASE_URL = "https://router.huggingface.co/v1"
V_ACTION_MODEL = "Qwen/Qwen3-VL-8B-Instruct:fastest"  # Vision-Language model for actions

HIGHLIGHT_DURATION = 1.5
HIGHLIGHT_SIZE = 100

# Safety settings
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


@dataclass
class ActionResult:
    """Result from V_action model"""
    action: str
    coordinate: Optional[Tuple[int, int]] = None
    coordinate2: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    raw: Optional[str] = None


def _get_client() -> OpenAI:
    """Get OpenAI client for HuggingFace router."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError(
            "HF_TOKEN not found in environment. "
            "Please set HF_TOKEN in your .env file for V_action vision model."
        )
    return OpenAI(base_url=HF_BASE_URL, api_key=token)


def _capture_screenshot(region: Optional[Dict[str, int]] = None, max_dim: Optional[int] = None) -> Tuple[str, str, Tuple[int, int]]:
    """
    Capture desktop screenshot.
    
    Returns:
        Tuple of (base64_data_url, file_path, (width, height))
    """
    with mss() as sct:
        mon = region or sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

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

        return data_url, path, (img.width, img.height)



def _v_action(instruction: str, screenshot_data_url: str, screen_size: Tuple[int, int]) -> ActionResult:
    """
    Call V_action vision model to get precise action coordinates.
    
    Args:
        instruction: Natural language instruction (from GNX engine)
        screenshot_data_url: Base64 encoded screenshot
        screen_size: Screen dimensions (width, height)
    
    Returns:
        ActionResult with action type and coordinates
    """
    system_prompt = (
        "You are V_action, a vision-based action executor for desktop automation. "
        "Given an instruction and screenshot, determine the exact action to perform.\n\n"
        "Return ONLY valid JSON with these fields:\n"
        "- action: one of 'click', 'double_click', 'right_click', 'type', 'scroll', 'drag', 'wait', 'terminate'\n"
        "- coordinate: [x, y] in 1000x1000 normalized grid (0-1000)\n"
        "- coordinate2: [x, y] for drag end point (only for drag action)\n"
        "- text: text to type (only for type action)\n"
        "- time: seconds to wait (only for wait action)\n"
        "- status: completion message (only for terminate action)\n\n"
        "Examples:\n"
        '{\"action\": \"click\", \"coordinate\": [500, 500]}\n'
        '{\"action\": \"type\", \"coordinate\": [500, 500], \"text\": \"hello\"}\n'
        '{\"action\": \"scroll\", \"coordinate\": [500, 500], \"text\": \"down\"}\n'
        '{\"action\": \"terminate\", \"status\": \"Task completed successfully\"}\n\n'
        "Important: For Windows taskbar/Start button, coordinates are typically near bottom-left."
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
        return ActionResult(action="error", status=str(e), raw=str(e))


def _parse_action_json(content: str) -> ActionResult:
    """Parse JSON response from V_action model."""
    # Try to extract JSON from response
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
            )
        except json.JSONDecodeError:
            pass
    
    # Fallback parsing for non-JSON format
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
        )
    except Exception:
        return ActionResult(action="error", status=f"Failed to parse: {content}")


def _to_pixels(coord: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
    """Convert normalized coordinates (0-1000) to screen pixels."""
    x, y = coord
    # If values are in 1000-based grid
    if x > 1 or y > 1:
        px = int(x / 1000.0 * screen_size[0])
        py = int(y / 1000.0 * screen_size[1])
    else:
        # If normalized 0-1
        px = int(x * screen_size[0])
        py = int(y * screen_size[1])
    return max(0, px), max(0, py)


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


def _execute_action(act: ActionResult, screen_size: Tuple[int, int]) -> str:
    """Execute the action on the desktop."""
    try:
        if act.action == "click" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.click()
            return f"Clicked at ({x}, {y})"
        
        elif act.action == "double_click" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.doubleClick()
            return f"Double-clicked at ({x}, {y})"
        
        elif act.action == "right_click" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.rightClick()
            return f"Right-clicked at ({x}, {y})"
        
        elif act.action == "type":
            if act.coordinate:
                x, y = _to_pixels(act.coordinate, screen_size)
                pyautogui.click(x, y)
                time.sleep(0.2)
            if act.text:
                pyautogui.typewrite(act.text, interval=0.05)
                return f"Typed: '{act.text}'"
            return "Type action but no text provided"
        
        elif act.action == "scroll" and act.coordinate:
            x, y = _to_pixels(act.coordinate, screen_size)
            pyautogui.moveTo(x, y)
            direction = act.text or "down"
            clicks = -3 if direction.lower() == "down" else 3
            pyautogui.scroll(clicks)
            return f"Scrolled {direction} at ({x}, {y})"
        
        elif act.action == "drag" and act.coordinate and act.coordinate2:
            x1, y1 = _to_pixels(act.coordinate, screen_size)
            x2, y2 = _to_pixels(act.coordinate2, screen_size)
            _show_highlight(x1, y1)
            pyautogui.moveTo(x1, y1)
            pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)
            return f"Dragged from ({x1}, {y1}) to ({x2}, {y2})"
        
        elif act.action == "wait":
            wait_time = act.time or 1.0
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


# ============================================================================
# LangChain Tools for GNX Engine
# ============================================================================

@tool
def computer_screenshot() -> str:
    """
    Capture a screenshot of the desktop for computer control.
    Returns the path to the saved screenshot and screen dimensions.
    Use this to see the current state of the desktop before giving instructions.
    """
    try:
        # Downscale to 512x512 specifically for LLM context control
        data_url, path, size = _capture_screenshot(max_dim=512)
        payload = {
            "type": "screenshot",
            "path": path,
            "width": size[0],
            "height": size[1],
            # Include the data URL (already 512x512) so the main model can "see" the image
            "data_url": data_url,
            "note": "Use computer_control to execute actions based on what you see."
        }
        return json.dumps(payload)
    except Exception as e:
        return f"Error capturing screenshot: {e}"


@tool
def computer_control(instruction: str) -> str:
    """
    Execute a computer control instruction using vision-based AI.
    
    The instruction should describe what UI element to interact with, for example:
    - "Click on the Start button"
    - "Click on the Chrome icon"
    - "Type 'hello world' in the search box"
    - "Double-click on the Calculator app"
    - "Scroll down in the window"
    
    Args:
        instruction: Natural language description of the action to perform
    
    Returns:
        Result of the action execution
    """
    try:
        # Capture current screen state
        data_url, path, screen_size = _capture_screenshot()
        
        # Get action from V_action model
        action_result = _v_action(instruction, data_url, screen_size)
        
        if action_result.action == "error":
            return f"V_action error: {action_result.status}"
        
        # Execute the action
        result = _execute_action(action_result, screen_size)
        
        # Build response
        response = f"Instruction: {instruction}\n"
        response += f"Action: {action_result.action}\n"
        if action_result.coordinate:
            px, py = _to_pixels(action_result.coordinate, screen_size)
            response += f"Coordinate: ({px}, {py})\n"
        response += f"Result: {result}"
        
        return response
    
    except Exception as e:
        return f"Computer control error: {e}"


@tool
def computer_type_text(text: str, press_enter: bool = False) -> str:
    """
    Type text at the current cursor position.
    
    Args:
        text: The text to type
        press_enter: Whether to press Enter after typing
    
    Returns:
        Confirmation of the typed text
    """
    try:
        pyautogui.typewrite(text, interval=0.03)
        if press_enter:
            pyautogui.press('enter')
        return f"Typed: '{text}'" + (" and pressed Enter" if press_enter else "")
    except Exception as e:
        return f"Error typing text: {e}"


@tool
def computer_hotkey(keys: str) -> str:
    """
    Press a keyboard hotkey combination.
    
    Args:
        keys: Comma-separated key names, e.g., "ctrl,c" or "alt,tab" or "win"
    
    Returns:
        Confirmation of the hotkey pressed
    """
    try:
        key_list = [k.strip().lower() for k in keys.split(",")]
        
        # Map common key names
        key_map = {
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "win": "win",
            "windows": "win",
            "cmd": "win",
            "enter": "enter",
            "return": "enter",
            "tab": "tab",
            "esc": "esc",
            "escape": "esc",
            "space": "space",
            "backspace": "backspace",
            "delete": "delete",
        }
        
        mapped_keys = [key_map.get(k, k) for k in key_list]
        pyautogui.hotkey(*mapped_keys)
        
        return f"Pressed hotkey: {'+'.join(mapped_keys)}"
    except Exception as e:
        return f"Error pressing hotkey: {e}"


# Export all tools
COMPUTER_USE_TOOLS = [
    computer_screenshot,
    computer_control,
    computer_type_text,
    computer_hotkey,
]
