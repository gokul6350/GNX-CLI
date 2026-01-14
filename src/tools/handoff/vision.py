"""
Vision Agent Handoff Tool - Allows Main Agent to delegate visual tasks.
"""

import time
from typing import Tuple

from langchain_core.tools import tool

from src.agents.vision import VisionAgent
from src.vision_client import ActionResult, to_pixels


def _create_desktop_executor():
    """Create desktop action executor function."""
    import pyautogui
    import threading
    import tkinter as tk
    
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    
    def show_highlight(x: int, y: int, duration: float = 1.5):
        def runner():
            size = 100
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
                pass
        threading.Thread(target=runner, daemon=True).start()
    
    def execute(act: ActionResult, screen_size: Tuple[int, int]) -> str:
        try:
            if act.action == "click" and act.coordinate:
                x, y = to_pixels(act.coordinate, screen_size)
                show_highlight(x, y)
                pyautogui.moveTo(x, y)
                time.sleep(0.2)
                pyautogui.click()
                return f"Clicked at ({x}, {y})"
            
            elif act.action == "double_click" and act.coordinate:
                x, y = to_pixels(act.coordinate, screen_size)
                show_highlight(x, y)
                pyautogui.moveTo(x, y)
                time.sleep(0.2)
                pyautogui.doubleClick()
                return f"Double-clicked at ({x}, {y})"
            
            elif act.action == "right_click" and act.coordinate:
                x, y = to_pixels(act.coordinate, screen_size)
                show_highlight(x, y)
                pyautogui.moveTo(x, y)
                time.sleep(0.2)
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
            
            elif act.action == "hotkey" and act.text:
                keys = [k.strip().lower() for k in act.text.split(",")]
                pyautogui.hotkey(*keys)
                return f"Pressed hotkey: {'+'.join(keys)}"
            
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
                show_highlight(x1, y1)
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
    
    return execute


def _create_mobile_executor():
    """Create mobile action executor function."""
    import subprocess
    
    from src.tools.mobile.screenshot import get_current_device
    
    ADB_EXE = "adb"
    
    def execute(act: ActionResult, screen_size: Tuple[int, int]) -> str:
        device_id = get_current_device()
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
                duration = act.time or 1000
                subprocess.run(
                    f"{ADB_EXE} {prefix}shell input swipe {x} {y} {x} {y} {int(duration)}",
                    shell=True, check=True
                )
                return f"Long-pressed at ({x}, {y}) for {duration}ms"
            
            elif act.action == "type":
                if act.coordinate:
                    x, y = to_pixels(act.coordinate, screen_size)
                    subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
                    time.sleep(0.3)
                if act.text:
                    escaped_text = act.text.replace(" ", "%s").replace("'", "\\'")
                    subprocess.run(f'{ADB_EXE} {prefix}shell input text "{escaped_text}"', shell=True, check=True)
                    return f"Typed: '{act.text}'"
                return "Type action but no text provided"
            
            elif act.action == "swipe" and act.coordinate and act.coordinate2:
                x1, y1 = to_pixels(act.coordinate, screen_size)
                x2, y2 = to_pixels(act.coordinate2, screen_size)
                duration = act.time or 300
                subprocess.run(
                    f"{ADB_EXE} {prefix}shell input swipe {x1} {y1} {x2} {y2} {int(duration)}",
                    shell=True, check=True
                )
                return f"Swiped from ({x1}, {y1}) to ({x2}, {y2})"
            
            elif act.action in ("swipe_up", "swipe_down", "swipe_left", "swipe_right"):
                x = screen_size[0] // 2
                if act.action == "swipe_up":
                    y1, y2 = int(screen_size[1] * 0.7), int(screen_size[1] * 0.3)
                    subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y1} {x} {y2} 300", shell=True, check=True)
                elif act.action == "swipe_down":
                    y1, y2 = int(screen_size[1] * 0.3), int(screen_size[1] * 0.7)
                    subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x} {y1} {x} {y2} 300", shell=True, check=True)
                elif act.action == "swipe_left":
                    y = screen_size[1] // 2
                    x1, x2 = int(screen_size[0] * 0.8), int(screen_size[0] * 0.2)
                    subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x1} {y} {x2} {y} 300", shell=True, check=True)
                elif act.action == "swipe_right":
                    y = screen_size[1] // 2
                    x1, x2 = int(screen_size[0] * 0.2), int(screen_size[0] * 0.8)
                    subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x1} {y} {x2} {y} 300", shell=True, check=True)
                return f"Swiped {act.action.replace('swipe_', '')}"
            
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
    
    return execute


@tool
def activate_vision_agent(task: str, mode: str = "desktop") -> str:
    """
    Activate the Vision Agent to perform complex visual tasks autonomously.
    
    Use this tool when you need to:
    - Interact with the screen based on visual feedback
    - Complete multi-step UI automation tasks
    - Click on elements you cannot locate by coordinates alone
    - Navigate desktop or mobile interfaces
    
    The Vision Agent will:
    1. Take screenshots to see the current state
    2. Use a Vision-Language Model to decide actions
    3. Execute actions (click, type, scroll, etc.)
    4. Repeat until the task is complete
    
    Args:
        task: Description of what to accomplish (e.g., "Open Spotify and play music")
        mode: Either 'desktop' for Windows/Mac or 'mobile' for Android phone
    
    Returns:
        Summary of what the Vision Agent accomplished, including action history.
    """
    agent = VisionAgent(mode=mode)
    
    if mode == "mobile":
        from src.tools.mobile.screenshot import capture_mobile_screenshot
        capture_fn = lambda: capture_mobile_screenshot(max_dim=512)
        execute_fn = _create_mobile_executor()
    else:
        from src.tools.desktop.screenshot import capture_desktop_screenshot
        capture_fn = lambda: capture_desktop_screenshot(max_dim=512)
        execute_fn = _create_desktop_executor()
    
    return agent.run(task, capture_fn, execute_fn)
