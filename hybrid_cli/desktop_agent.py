import base64
import io
import json
import os
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List

import pyautogui
from mss import mss
from openai import OpenAI
from PIL import Image

HF_BASE_URL = "https://router.huggingface.co/v1"
PLANNER_MODEL = "google/gemma-3-27b-it:scaleway"
ACTION_MODEL = "Qwen/Qwen3-VL-8B-Instruct:fastest"
HF_TOKEN_DEFAULT = "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"

HIGHLIGHT_DURATION = 2.0
HIGHLIGHT_SIZE = 120

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


@dataclass
class PlannerResult:
    instruction: str


@dataclass
class ActionResult:
    action: str
    coordinate: Optional[Tuple[int, int]] = None
    coordinate2: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    raw: Optional[str] = None


def _client() -> OpenAI:
    token = os.environ["HF_TOKEN"]
    return OpenAI(base_url=HF_BASE_URL, api_key=token)


def capture_screenshot(region: Optional[Dict[str, int]] = None) -> Tuple[str, str, Tuple[int, int]]:
    with mss() as sct:
        mon = region or sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        path = os.path.join(os.getcwd(), "desktop_last.png")
        img.save(path)
        return data_url, path, (shot.width, shot.height)


def planner(goal: str, screenshot_data_url: str, screen_size: Tuple[int, int], history: List[str]) -> PlannerResult:
    history_text = " -> ".join(history) if history else "None"
    system_prompt = (
        "You are the high-level planner (A1). Look at the desktop screen and the history."
        " Return exactly ONE primitive step for a desktop action agent to achieve the user goal."
        " Allowed verbs: 'Click ...' OR 'Type ...' OR 'Wait ...' OR 'Terminate'."
        " Do NOT give screen coordinates or numbers; describe the UI element instead (e.g., 'Click the Start button')."
        " If the goal is already achieved, move to the next logical step or terminate."
        " No chaining, no 'then'."
    )
    resp = _client().chat.completions.create(
        model=PLANNER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"User goal: {goal}\nScreen size: {screen_size[0]}x{screen_size[1]}\nPrevious steps: {history_text}\nReturn one next step."},
                    {"type": "image_url", "image_url": {"url": screenshot_data_url}},
                ],
            },
        ],
        temperature=0.2,
        max_tokens=120,
    )
    return PlannerResult(instruction=resp.choices[0].message.content.strip())


def action(instruction: str, screenshot_data_url: str, screen_size: Tuple[int, int]) -> ActionResult:
    system_prompt = (
        "You are the action agent (slave). Execute the planner instruction on the screenshot. "
        "Return ONLY JSON: action (click|swipe|type|wait|terminate), coordinate, coordinate2, text, time, status. "
        "Coordinates must be in 1000x1000 grid (0-1000)."
        " Example: {\"action\": \"click\", \"coordinate\": [500, 500], \"text\": \"\", \"time\": 0, \"status\": \"\"}"
        " If asked to click Windows Start, target the bottom-left Windows logo."
    )
    resp = _client().chat.completions.create(
        model=ACTION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Instruction: {instruction}. Screen size: {screen_size[0]}x{screen_size[1]}"},
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


def _parse_action_json(content: str) -> ActionResult:
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        try:
            obj = json.loads(content[start : end + 1])
            c1 = obj.get("coordinate")
            c2 = obj.get("coordinate2")
            return ActionResult(
                action=obj.get("action"),
                coordinate=tuple(c1) if c1 else None,
                coordinate2=tuple(c2) if c2 else None,
                text=obj.get("text"),
                time=obj.get("time"),
                status=obj.get("status"),
            )
        except json.JSONDecodeError:
            pass
            
    # Fallback for non-JSON format
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
            action=data.get("action"),
            coordinate=tuple(c1) if c1 else None,
            coordinate2=tuple(c2) if c2 else None,
            text=data.get("text"),
            time=data.get("time"),
            status=data.get("status"),
        )
    except Exception:
        raise ValueError(f"No JSON object found and fallback failed: {content}")


def _to_px(coord: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
    x, y = coord
    # If values look like pixels (>1), assume 1000-based normalization for Qwen-VL
    if x > 1 or y > 1:
        px = int(x / 1000.0 * screen_size[0])
        py = int(y / 1000.0 * screen_size[1])
    else:
        px = int(x * screen_size[0])
        py = int(y * screen_size[1])
    return max(0, px), max(0, py)


def _adjust(act: ActionResult, instruction: str, screen_size: Tuple[int, int]) -> ActionResult:
    if act.action != "click" or not act.coordinate:
        return act
    w, h = screen_size
    text_lower = instruction.lower()
    if "start" in text_lower:
        act.coordinate = (max(24, int(w * 0.035)), max(h - 28, int(h * 0.97)))
    return act


def _overlay(x: int, y: int, duration: float = HIGHLIGHT_DURATION) -> None:
    def runner():
        size = HIGHLIGHT_SIZE
        left = int(x - size / 2)
        top = int(y - size / 2)
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", "magenta")
        root.configure(bg="magenta")
        root.geometry(f"{size}x{size}+{left}+{top}")
        canvas = tk.Canvas(root, width=size, height=size, highlightthickness=0, bg="magenta")
        canvas.pack()
        canvas.create_oval(4, 4, size - 4, size - 4, fill="", outline="red", width=6)
        root.after(int(duration * 1000), root.destroy)
        root.mainloop()

    threading.Thread(target=runner, daemon=True).start()


def execute(act: ActionResult, instruction: str, screen_size: Tuple[int, int], dry_run: bool = False) -> None:
    if dry_run:
        print("(dry run) skipping execution")
        return
    # act = _adjust(act, instruction, screen_size)  # Removed: Trust the VL model's coordinates
    if act.action == "click" and act.coordinate:
        x, y = _to_px(act.coordinate, screen_size)
        print(f"Executing click at: ({x}, {y}) px")
        _overlay(x, y)
        pyautogui.moveTo(x, y)
        time.sleep(0.5)
        pyautogui.click()
    elif act.action == "type" and act.text is not None:
        pyautogui.typewrite(act.text)
    elif act.action == "wait" and act.time is not None:
        time.sleep(float(act.time))
    elif act.action == "swipe" and act.coordinate and act.coordinate2:
        x1, y1 = _to_px(act.coordinate, screen_size)
        x2, y2 = _to_px(act.coordinate2, screen_size)
        _overlay(x1, y1)
        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=0.3)
    elif act.action == "terminate" and act.status:
        print(f"Terminate: {act.status}")
    else:
        print(f"Unknown or incomplete action: {act}")


def run(goal: str, region: Optional[Dict[str, int]] = None, dry_run: bool = False) -> None:
    history: List[str] = []
    max_steps = 15
    
    for i in range(max_steps):
        print(f"\n--- Step {i+1}/{max_steps} ---")
        step_start = time.time()

        data_url, path, size = capture_screenshot(region)
        print(f"Captured screenshot: {path} size={size}")
        
        t0 = time.time()
        plan = planner(goal, data_url, size, history)
        planner_time = time.time() - t0
        print(f"Planner instruction: {plan.instruction}")
        
        if "terminate" in plan.instruction.lower():
            print("Planner decided to terminate.")
            break
            
        t0 = time.time()
        act = action(plan.instruction, data_url, size)
        action_time = time.time() - t0
        print("Action raw:")
        print(act.raw)
        print("Parsed action:", act)
        
        if act.action == "terminate":
            print(f"Action agent terminated: {act.status}")
            break
            
        execute(act, plan.instruction, size, dry_run=dry_run)
        history.append(plan.instruction)
        
        step_time = time.time() - step_start
        print(f"Logs: Planner took {planner_time:.2f}s, Action took {action_time:.2f}s, Total step completed in {step_time:.2f}s")
        3
        time.sleep(2)  # Wait for UI to settle
