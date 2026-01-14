"""
Mobile Tools Package - Atomic mobile automation tools via ADB.
"""

from .screenshot import (
    mobile_screenshot, 
    capture_mobile_screenshot, 
    get_current_device, 
    set_current_device
)
from .touch import (
    mobile_tap, 
    mobile_double_tap, 
    mobile_long_press, 
    mobile_swipe, 
    mobile_swipe_direction
)
from .keyboard import mobile_type, mobile_keyevent
from .system import (
    mobile_devices, 
    mobile_connect, 
    mobile_home, 
    mobile_back, 
    mobile_recent, 
    mobile_power, 
    mobile_volume
)

# All mobile tools for registration
MOBILE_TOOLS = [
    mobile_devices,
    mobile_connect,
    mobile_screenshot,
    mobile_tap,
    mobile_double_tap,
    mobile_long_press,
    mobile_swipe,
    mobile_swipe_direction,
    mobile_type,
    mobile_keyevent,
    mobile_home,
    mobile_back,
    mobile_recent,
    mobile_power,
    mobile_volume,
]

__all__ = [
    "mobile_screenshot",
    "capture_mobile_screenshot",
    "get_current_device",
    "set_current_device",
    "mobile_tap",
    "mobile_double_tap",
    "mobile_long_press",
    "mobile_swipe",
    "mobile_swipe_direction",
    "mobile_type",
    "mobile_keyevent",
    "mobile_devices",
    "mobile_connect",
    "mobile_home",
    "mobile_back",
    "mobile_recent",
    "mobile_power",
    "mobile_volume",
    "MOBILE_TOOLS",
]
