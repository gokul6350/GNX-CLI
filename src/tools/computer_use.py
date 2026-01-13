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
from typing import Optional, Tuple, Dict

import pyautogui
from mss import mss
from PIL import Image
from langchain_core.tools import tool
from dotenv import load_dotenv

from src.gnx_engine.vl_provider import query_vl_model, to_pixels, ActionResult, log_step

# Ensure .env is loaded and OVERRIDES any existing env vars
load_dotenv(override=True)

HIGHLIGHT_DURATION = 1.5
HIGHLIGHT_SIZE = 100

# Safety settings
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05





def _capture_screenshot(region: Optional[Dict[str, int]] = None, max_dim: Optional[int] = None) -> Tuple[str, str, Tuple[int, int], Tuple[int, int]]:
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
        "- description: brief description of the element (e.g., 'Start button', 'Chrome icon')\n"
        "- time: seconds to wait (only for wait action)\n"
        "- status: completion message (only for terminate action)\n\n"
        "CRITICAL RULES:\n"
        "1. If the target element is NOT visible, do NOT guess coordinates.\n"
        "2. If the element is definitely not found, return: {\"action\": \"terminate\", \"status\": \"Element not found\"}\n\n"
        "Examples:\n"
        '{\"action\": \"click\", \"coordinate\": [500, 500], \"description\": \"Start button\"}\n'
        '{\"action\": \"type\", \"coordinate\": [500, 500], \"text\": \"hello\", \"description\": \"Search box\"}\n'
        '{\"action\": \"scroll\", \"coordinate\": [500, 500], \"text\": \"down\"}\n'
        '{\"action\": \"terminate\", \"status\": \"Task completed successfully\"}\n\n'
        "Important: For Windows taskbar/Start button, coordinates are typically near bottom-left."
    )
    
    user_text = f"Instruction: {instruction}\nScreen size: {screen_size[0]}x{screen_size[1]}"
    
    return query_vl_model(system_prompt, user_text, screenshot_data_url)


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
            x, y = to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.click()
            return f"Clicked at ({x}, {y})"
        
        elif act.action == "double_click" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.doubleClick()
            return f"Double-clicked at ({x}, {y})"
        
        elif act.action == "right_click" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            _show_highlight(x, y)
            pyautogui.moveTo(x, y)
            time.sleep(0.3)
            pyautogui.rightClick()
            return f"Right-clicked at ({x}, {y})"
        
        elif act.action == "type":
            if act.coordinate:
                x, y = to_pixels(act.coordinate, screen_size)
                pyautogui.click(x, y)
                time.sleep(0.2)
            if act.text:
                pyautogui.typewrite(act.text, interval=0.05)
                return f"Typed: '{act.text}'"
            return "Type action but no text provided"
        
        elif act.action == "scroll" and act.coordinate:
            x, y = to_pixels(act.coordinate, screen_size)
            pyautogui.moveTo(x, y)
            direction = act.text or "down"
            clicks = -3 if direction.lower() == "down" else 3
            pyautogui.scroll(clicks)
            return f"Scrolled {direction} at ({x}, {y})"
        
        elif act.action == "drag" and act.coordinate and act.coordinate2:
            x1, y1 = to_pixels(act.coordinate, screen_size)
            x2, y2 = to_pixels(act.coordinate2, screen_size)
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
        data_url, path, size, _ = _capture_screenshot(max_dim=512)
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
    total_start = log_step(f"Computer Control: {instruction[:50]}...")
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
        # Resize to 512x512 to prevent timeouts with large payloads
        data_url, path, screen_size, original_size = _capture_screenshot(max_dim=512)
        
        # Get action from V_action model
        action_result = _v_action(instruction, data_url, screen_size)
        
        if action_result.action == "error":
            log_step("Computer Control (Error)", total_start)
            return f"V_action error: {action_result.status}"
        
        # Execute the action
        exec_start = log_step(f"Executing Action: {action_result.action}")
        result = _execute_action(action_result, original_size)
        log_step("Action Execution", exec_start)
        
        # Build response
        response = f"Instruction: {instruction}\n"
        response += f"Action: {action_result.action}\n"
        if action_result.description:
            response += f"Description: {action_result.description}\n"
        if action_result.coordinate:
            px, py = to_pixels(action_result.coordinate, original_size)
            response += f"Coordinate: ({px}, {py})\n"
        response += f"Result: {result}"
        
        log_step("Computer Control", total_start)
        return response
    
    except Exception as e:
        log_step("Computer Control (Exception)", total_start)
        return f"Computer control error: {e}"


@tool
def computer_type_text(text: str, press_enter: str = "False") -> str:
    """
    Type text at the current cursor position.
    
    Args:
        text: The text to type
        press_enter: Whether to press Enter after typing (true/false)
    
    Returns:
        Confirmation of the typed text
    """
    try:
        pyautogui.typewrite(text, interval=0.03)
        
        # Handle string boolean from LLM
        should_enter = str(press_enter).lower() == "true"
        
        if should_enter:
            pyautogui.press('enter')
        return f"Typed: '{text}'" + (" and pressed Enter" if should_enter else "")
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
