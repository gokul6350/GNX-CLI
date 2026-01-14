"""
Mobile System Operations - Device connection, Home, Back, etc.
"""

import subprocess

from langchain_core.tools import tool

from .screenshot import get_current_device, set_current_device

ADB_EXE = "adb"


@tool
def mobile_devices() -> str:
    """
    List connected Android devices via ADB.
    Use this to check which devices are available for mobile control.
    
    Returns:
        List of connected device IDs.
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
        device_id: The device ID to connect to (optional).
    
    Returns:
        Connection status.
    """
    try:
        if device_id:
            set_current_device(device_id)
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
                set_current_device(devices[0])
                return f"Connected to device: {devices[0]}"
            else:
                return "No devices available. Please connect a device first."
    except Exception as e:
        return f"Connection error: {e}"


@tool
def mobile_home() -> str:
    """
    Press the home button on the mobile device.
    
    Returns:
        Confirmation.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_HOME", shell=True, check=True)
        return "Pressed home button"
    except Exception as e:
        return f"Home button error: {e}"


@tool
def mobile_back() -> str:
    """
    Press the back button on the mobile device.
    
    Returns:
        Confirmation.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_BACK", shell=True, check=True)
        return "Pressed back button"
    except Exception as e:
        return f"Back button error: {e}"


@tool
def mobile_recent() -> str:
    """
    Press the recent apps button on the mobile device.
    
    Returns:
        Confirmation.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_APP_SWITCH", shell=True, check=True)
        return "Pressed recent apps button"
    except Exception as e:
        return f"Recent apps error: {e}"


@tool
def mobile_power() -> str:
    """
    Press the power button on the mobile device.
    
    Returns:
        Confirmation.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent KEYCODE_POWER", shell=True, check=True)
        return "Pressed power button"
    except Exception as e:
        return f"Power button error: {e}"


@tool
def mobile_volume(direction: str = "up") -> str:
    """
    Adjust volume on the mobile device.
    
    Args:
        direction: 'up' or 'down'.
    
    Returns:
        Confirmation.
    """
    device_id = get_current_device()
    prefix = f"-s {device_id} " if device_id else ""
    
    keycode = "KEYCODE_VOLUME_UP" if direction.lower() == "up" else "KEYCODE_VOLUME_DOWN"
    
    try:
        subprocess.run(f"{ADB_EXE} {prefix}shell input keyevent {keycode}", shell=True, check=True)
        return f"Volume {direction}"
    except Exception as e:
        return f"Volume error: {e}"
