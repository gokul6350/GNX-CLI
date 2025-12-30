import base64
import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from PIL import Image

HF_BASE_URL = "https://router.huggingface.co/v1"
PLANNER_MODEL = "aisingapore/Qwen-SEA-LION-v4-32B-IT:publicai"  # text-only
ACTION_MODEL = "Qwen/Qwen3-VL-8B-Instruct:fastest"  # vision
HF_TOKEN_DEFAULT = "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"

ADB_EXE = "adb"  # assumes adb in PATH

@dataclass
class PlannerResult:
    instruction: str


@dataclass
class ActionResult:
    action: str
    coordinate: Optional[Tuple[int, int]] = None  # normalized 0-1
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    raw: Optional[str] = None


def _client() -> OpenAI:
    token = os.environ.get("HF_TOKEN") or HF_TOKEN_DEFAULT
    return OpenAI(base_url=HF_BASE_URL, api_key=token)


def _adb(cmd: str) -> str:
    res = subprocess.run(f"{ADB_EXE} {cmd}", shell=True, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def capture_screenshot(device_id: Optional[str] = None) -> Tuple[str, str, Tuple[int, int]]:
    prefix = f"-s {device_id} " if device_id else ""
    remote = "/sdcard/cli_ss.png"
    local = os.path.join(os.getcwd(), "mobile_last.png")
    subprocess.run(f"{ADB_EXE} {prefix}shell screencap -p {remote}", shell=True, check=True, capture_output=True, text=True)
    subprocess.run(f"{ADB_EXE} {prefix}pull {remote} {local}", shell=True, check=True, capture_output=True, text=True)
    subprocess.run(f"{ADB_EXE} {prefix}shell rm {remote}", shell=True, check=True, capture_output=True, text=True)
    img = Image.open(local)
    w, h = img.size
    with open(local, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    data_url = f"data:image/png;base64,{b64}"
    return data_url, local, (w, h)


def planner(goal: str, screenshot_data_url: str, screen_size: Tuple[int, int], history: List[str]) -> PlannerResult:
    history_text = " -> ".join(history) if history else "None"
    system_prompt = (
        "You are the high-level planner (A1). Look at the phone screen and the history."
        " Return exactly ONE primitive step for a phone action agent to achieve the user goal."
        " Allowed verbs: 'Tap ...' OR 'Type ...' OR 'Wait ...' OR 'Terminate'."
        " Do NOT give screen coordinates or numbers; describe the UI element instead (e.g., 'Tap the WhatsApp icon on home screen')."
        " If the goal is already achieved or the app is already open, move to the next logical step."
        " No chaining, no 'then'."
    )
    resp = _client().chat.completions.create(
        model=ACTION_MODEL,
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
        "You are the action agent. Execute the planner instruction on the phone screenshot."
        " Return ONLY JSON: action (tap|swipe|type|wait|terminate), coordinate [x,y], text, time, status."
        " Coordinates must be in 1000x1000 grid (0-1000)."
        " Example: {\"action\": \"tap\", \"coordinate\": [500, 500], \"text\": \"\", \"time\": 0, \"status\": \"\"}"
        " If terminate, set status."
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
            coord = obj.get("coordinate")
            return ActionResult(
                action=obj.get("action"),
                coordinate=tuple(coord) if coord else None,
                text=obj.get("text"),
                time=obj.get("time"),
                status=obj.get("status"),
            )
        except json.JSONDecodeError:
            pass
    
    # Fallback for non-JSON format like "action: tap, coordinate: [127, 916], ..."
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
        
        coord = data.get("coordinate")
        return ActionResult(
            action=data.get("action"),
            coordinate=tuple(coord) if coord else None,
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


def execute(act: ActionResult, instruction: str, screen_size: Tuple[int, int], device_id: Optional[str] = None, dry_run: bool = False) -> None:
    prefix = f"-s {device_id} " if device_id else ""
    if dry_run:
        print("(dry run) skipping execution")
        return

    if act.action == "tap" and act.coordinate:
        x, y = _to_px(act.coordinate, screen_size)
        subprocess.run(f"{ADB_EXE} {prefix}shell input tap {x} {y}", shell=True, check=True)
    elif act.action == "type" and act.text is not None:
        txt = act.text.replace(" ", "%s")
        subprocess.run(f"{ADB_EXE} {prefix}shell input text \"{txt}\"", shell=True, check=True)
    elif act.action == "wait" and act.time is not None:
        time.sleep(float(act.time) / 1000.0 if act.time and act.time > 5 else float(act.time))
    elif act.action == "swipe" and act.coordinate and act.coordinate2:
        x1, y1 = _to_px(act.coordinate, screen_size)
        x2, y2 = _to_px(act.coordinate2, screen_size)
        subprocess.run(f"{ADB_EXE} {prefix}shell input swipe {x1} {y1} {x2} {y2} 300", shell=True, check=True)
    elif act.action == "terminate" and act.status:
        print(f"Terminate: {act.status}")
    else:
        print(f"Unknown or incomplete action: {act}")


def run(goal: str, device_id: Optional[str] = None, dry_run: bool = False) -> None:
    history: List[str] = []
    max_steps = 15
    
    for i in range(max_steps):
        print(f"\n--- Step {i+1}/{max_steps} ---")
        step_start = time.time()

        data_url, path, size = capture_screenshot(device_id)
        print(f"Captured phone screenshot: {path} size={size}")
        
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
            
        execute(act, plan.instruction, size, device_id=device_id, dry_run=dry_run)
        history.append(plan.instruction)
        
        step_time = time.time() - step_start
        print(f"Logs: Planner took {planner_time:.2f}s, Action took {action_time:.2f}s, Total step completed in {step_time:.2f}s")

        time.sleep(2)  # Wait for UI to settle
