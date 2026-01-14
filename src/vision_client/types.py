"""
Data types for Vision Client.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ActionResult:
    """Result from Vision Model action parsing."""
    action: str
    coordinate: Optional[Tuple[int, int]] = None
    coordinate2: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None
    raw: Optional[str] = None


def to_pixels(coord: Tuple[float, float], screen_size: Tuple[int, int]) -> Tuple[int, int]:
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
