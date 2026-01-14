"""
Output parser for Vision Agent responses.
"""

import json
from typing import Optional, Tuple
from src.vision_client.types import ActionResult


def _normalize_coordinate(coord: Tuple[float, float]) -> Tuple[int, int]:
    """
    Normalize coordinates to 0-1000 range.
    If model outputs values > 1000, clamp them or try to interpret as percentages.
    """
    x, y = coord
    
    # If coordinates are way out of range (like pixel values), 
    # the model might have hallucinated - clamp to valid range
    if x > 1000:
        x = min(1000, x)  # Clamp to max
    if y > 1000:
        y = min(1000, y)
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    
    return (int(x), int(y))


def parse_action_json(content: str) -> ActionResult:
    """
    Parse JSON response from Vision model.
    Tries to extract JSON block, handles common formatting issues.
    Expects a SINGLE valid JSON object as the first complete JSON in the response.
    """
    # Try to extract the FIRST valid JSON object from response
    start = content.find("{")
    
    if start == -1:
        return ActionResult(action="error", status=f"No JSON found in response", raw=content)
    
    # Find the matching closing brace for the first opening brace
    brace_count = 0
    end = -1
    for i in range(start, len(content)):
        if content[i] == "{":
            brace_count += 1
        elif content[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    
    if end == -1:
        return ActionResult(action="error", status=f"Incomplete JSON in response", raw=content)
    
    try:
        json_str = content[start:end+1]
        # Fix common JSON errors if needed (like single quotes)
        if "'" in json_str and '"' not in json_str:
            json_str = json_str.replace("'", '"')
        
        data = json.loads(json_str)
        
        c1 = data.get("coordinate")
        c2 = data.get("coordinate2")
        
        # Normalize coordinates to valid 0-1000 range
        if c1:
            c1 = _normalize_coordinate(tuple(c1))
        if c2:
            c2 = _normalize_coordinate(tuple(c2))
        
        return ActionResult(
            action=data.get("action", "unknown"),
            coordinate=c1,
            coordinate2=c2,
            text=data.get("text"),
            time=data.get("time"),
            status=data.get("status"),
            description=data.get("description"),
            raw=content,
        )
    except json.JSONDecodeError as e:
        return ActionResult(action="error", status=f"JSON parse error: {str(e)}", raw=content)
