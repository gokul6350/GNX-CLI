"""
Desktop Keyboard Operations - Type, Hotkey.
"""

import pyautogui
from langchain_core.tools import tool

# Safety settings
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


@tool
def desktop_type(text: str, interval: float = 0.03) -> str:
    """
    Type text at the current cursor position.
    
    Args:
        text: The text to type.
        interval: Delay between keystrokes in seconds.
    
    Returns:
        Confirmation of the typed text.
    """
    try:
        pyautogui.typewrite(text, interval=interval)
        return f"Typed: '{text}'"
    except Exception as e:
        return f"Type error: {e}"


@tool
def desktop_type_unicode(text: str) -> str:
    """
    Type text including unicode characters (non-ASCII).
    Use this for special characters, emojis, or non-English text.
    
    Args:
        text: The text to type (supports unicode).
    
    Returns:
        Confirmation of the typed text.
    """
    try:
        pyautogui.write(text)  # write() supports unicode
        return f"Typed (unicode): '{text}'"
    except Exception as e:
        return f"Type error: {e}"


@tool
def desktop_hotkey(keys: str) -> str:
    """
    Press a keyboard hotkey combination.
    
    Args:
        keys: Comma-separated key names, e.g., "ctrl,c" or "alt,tab" or "win"
    
    Returns:
        Confirmation of the hotkey pressed.
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
        return f"Hotkey error: {e}"


@tool
def desktop_press(key: str) -> str:
    """
    Press a single key.
    
    Args:
        key: Key name (e.g., 'enter', 'tab', 'escape', 'f1', etc.)
    
    Returns:
        Confirmation of the key press.
    """
    try:
        pyautogui.press(key)
        return f"Pressed key: {key}"
    except Exception as e:
        return f"Key press error: {e}"
