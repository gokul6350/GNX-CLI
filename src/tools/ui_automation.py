"""UI automation tools for element-level desktop navigation."""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import tool
from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.findwindows import ElementNotFoundError

SCREENSHOT_DIR = Path("ui_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _normalize(text: Optional[str]) -> str:
    return text.lower() if text else ""


def _find_window(title: str) -> BaseWrapper:
    desktop = Desktop(backend="uia")
    normalized_title = title.lower()
    partial_matches = []

    for win in desktop.windows():
        info = win.element_info
        name = _normalize(info.name)
        if name == normalized_title:
            return win
        if normalized_title and normalized_title in name:
            partial_matches.append(win)

    if partial_matches:
        return partial_matches[0]

    raise ElementNotFoundError(f"No window found matching '{title}'")


def _describe_element(wrapper: BaseWrapper, depth: int, max_depth: int, lines: List[str]) -> None:
    info = wrapper.element_info
    label = info.name or info.automation_id or "<unnamed>"
    lines.append(f"{'  ' * depth}- {info.control_type}: {label}")

    if depth >= max_depth:
        if wrapper.children():
            lines.append(f"{'  ' * (depth + 1)}... (truncated)")
        return

    for child in wrapper.children():
        _describe_element(child, depth + 1, max_depth, lines)


def _find_element(root: BaseWrapper, query: str) -> BaseWrapper:
    normalized_query = query.lower()
    queue = [root]

    while queue:
        current = queue.pop(0)
        info = current.element_info
        name = _normalize(info.name)
        automation_id = _normalize(info.automation_id)
        class_name = _normalize(info.class_name)

        if normalized_query in name or normalized_query in automation_id or normalized_query in class_name:
            return current

        queue.extend(current.children())

    raise ElementNotFoundError(f"No element found containing '{query}'")


@tool
def ui_list_windows() -> str:
    """List all top-level windows visible through UI Automation."""
    try:
        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        if not windows:
            return "No windows detected."

        lines = ["Detected windows:"]
        for win in windows:
            info = win.element_info
            title = info.name or "<untitled>"
            handle = info.handle
            lines.append(f"- {title} (handle: {handle})")

        return "\n".join(lines)
    except Exception as exc:
        return f"Error listing windows: {exc}"


@tool
def ui_scan_ui_tree(window_title: str, max_depth: int = 4) -> str:
    """Walk the UI Automation tree for the requested window."""
    try:
        target = _find_window(window_title)
        lines: List[str] = []
        _describe_element(target, depth=0, max_depth=max_depth, lines=lines)
        return "\n".join(lines)
    except ElementNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error scanning UI tree: {exc}"


@tool
def ui_click_element(window_title: str, element_name: str) -> str:
    """Click the first element whose name or automation id matches the query."""
    try:
        window = _find_window(window_title)
        element = _find_element(window, element_name)
        element.click_input()
        info = element.element_info
        return f"Clicked {info.control_type}: {info.name or info.automation_id or '<unnamed>'}"
    except ElementNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error clicking element: {exc}"


@tool
def ui_type_into_element(window_title: str, text: str, element_name: Optional[str] = None) -> str:
    """Type text into a named element (or the window itself if no name provided)."""
    try:
        window = _find_window(window_title)
        target = window if not element_name else _find_element(window, element_name)
        target.set_focus()
        target.type_keys(text, with_spaces=True, pause=0.03)
        return f"Typed '{text}' into {window_title}"
    except ElementNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error typing into element: {exc}"


@tool
def ui_capture_window_screenshot(window_title: str) -> str:
    """Capture a screenshot of the requested window."""
    try:
        window = _find_window(window_title)
        image = window.capture_as_image()
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r"[^A-Za-z0-9_]+", "_", window_title)[:32]
        target_path = SCREENSHOT_DIR / f"window_{safe_title}_{stamp}.png"
        image.save(target_path)
        return f"Screenshot saved: {target_path.resolve()}"
    except ElementNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Error capturing screenshot: {exc}"


UI_AUTOMATION_TOOLS = [
    ui_list_windows,
    ui_scan_ui_tree,
    ui_click_element,
    ui_type_into_element,
    ui_capture_window_screenshot,
]
