import os
import json
import logging
import time
import datetime
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

# Try to import config, handle if not found (e.g. running standalone)
try:
    import config
except ImportError:
    config = None

# Load environment variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Default Configuration
DEFAULT_HF_BASE_URL = "https://router.huggingface.co/v1"
DEFAULT_V_ACTION_MODEL = "Qwen/Qwen3-VL-8B-Instruct:fastest"

def log_step(step_name, start_time=None):
    current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if start_time:
        duration = time.time() - start_time
        print(f"[{current_time}] [COMPLETED] {step_name} (Took: {duration:.4f}s)")
    else:
        print(f"[{current_time}] [STARTED] {step_name}")
    return time.time()

@dataclass
class ActionResult:
    """Result from V_action model"""
    action: str
    coordinate: Optional[Tuple[int, int]] = None
    coordinate2: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    time: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None
    raw: Optional[str] = None

def get_vl_config() -> Dict[str, str]:
    """
    Get configuration for Vision-Language Provider.
    Prioritizes config.py, then environment variables, then defaults.
    """
    # Get provider from config or env
    provider = "huggingface"
    if config and hasattr(config, "VL_PROVIDER"):
        provider = config.VL_PROVIDER
    else:
        provider = os.environ.get("VL_PROVIDER", "huggingface")
    
    if provider == "custom":
        base_url = None
        if config and hasattr(config, "VL_BASE_URL"):
            base_url = config.VL_BASE_URL
        else:
            base_url = os.environ.get("VL_BASE_URL")
            
        api_key = "dummy"
        if config and hasattr(config, "VL_API_KEY"):
            api_key = config.VL_API_KEY
        else:
            api_key = os.environ.get("VL_API_KEY", "dummy")
            
        model = "NexaAI/Qwen3-VL-2B-Instruct-GGUF"
        if config and hasattr(config, "VL_MODEL"):
            model = config.VL_MODEL
        else:
            model = os.environ.get("VL_MODEL", "NexaAI/Qwen3-VL-2B-Instruct-GGUF")

        return {
            "provider": "custom",
            "base_url": base_url,
            "api_key": api_key,
            "model": model
        }
    else:
        # Default to HuggingFace
        token = os.environ.get("HF_TOKEN")
        return {
            "provider": "huggingface",
            "base_url": DEFAULT_HF_BASE_URL,
            "api_key": token,
            "model": DEFAULT_V_ACTION_MODEL
        }

def get_vl_client() -> OpenAI:
    """Get OpenAI client based on configuration."""
    conf = get_vl_config()
    
    if conf["provider"] == "huggingface":
        token = conf["api_key"]
        if not token:
            raise ValueError(
                "HF_TOKEN not found in environment. "
                "Please set HF_TOKEN in your .env file for V_action vision model. "
                "Get a valid token from: https://huggingface.co/settings/tokens"
            )
        if token.startswith("your_") or len(token) < 10:
            raise ValueError(f"Invalid HF_TOKEN: '{token}'")
            
        # Debug: Show what token is being used (masked)
        masked_token = token[:10] + "..." + token[-5:] if len(token) > 15 else "***"
        logger.debug(f"Using HF_TOKEN: {masked_token}")
            
        return OpenAI(base_url=conf["base_url"], api_key=token)
        
    elif conf["provider"] == "custom":
        base_url = conf["base_url"]
        if not base_url:
             raise ValueError("VL_BASE_URL not set for custom provider.")
             
        # Ensure base_url doesn't end with /chat/completions if using OpenAI client
        if base_url.endswith("/chat/completions"):
            base_url = base_url.replace("/chat/completions", "")
        if base_url.endswith("/v1/"):
             base_url = base_url[:-1] 
        elif not base_url.endswith("/v1"):
             base_url = f"{base_url}/v1"
        
        return OpenAI(base_url=base_url, api_key=conf["api_key"])
        
    return None

def query_vl_model(system_prompt: str, user_text: str, image_data_url: str, temperature: float = 0.1, max_tokens: int = 200) -> ActionResult:
    """
    Query the Vision-Language model and return parsed ActionResult.
    """
    step_start = log_step("Query VL Model")
    
    conf = get_vl_config()
    client = get_vl_client()
    model = conf["model"]
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ]
        
        # DEBUG: Save request payload to file
        try:
            debug_payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            with open("last_vl_request.json", "w", encoding="utf-8") as f:
                json.dump(debug_payload, f, indent=2)
            print(f"DEBUG: Request payload saved to last_vl_request.json")
        except Exception as e:
            print(f"DEBUG: Failed to save request payload: {e}")

        log_step(f"Sending request to {conf.get('base_url')} (Model: {model})")
        req_start = time.time()
        
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        log_step("VL Model Request", req_start)
        
        raw = resp.choices[0].message.content
        act = parse_action_json(raw)
        act.raw = raw
        
        log_step("Query VL Model", step_start)
        return act
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in query_vl_model: {error_msg}")
        # Better error messages for auth failures
        if "401" in error_msg or "Invalid username" in error_msg or "Unauthorized" in error_msg:
            if conf["provider"] == "huggingface":
                error_msg += "\nHint: Check your HF_TOKEN in .env file."
        
        log_step("Query VL Model (Failed)", step_start)
        return ActionResult(action="error", status=error_msg, raw=str(e))

def parse_action_json(content: str) -> ActionResult:
    """
    Parse JSON response from V_action model.
    Tries to extract JSON block, handles common formatting issues.
    """
    # Try to extract JSON from response
    start = content.find("{")
    end = content.rfind("}")
    
    if start != -1 and end != -1:
        try:
            json_str = content[start:end+1]
            # Fix common JSON errors if needed (like single quotes)
            if "'" in json_str and '"' not in json_str:
                json_str = json_str.replace("'", '"')
            data = json.loads(json_str)
            
            c1 = data.get("coordinate")
            c2 = data.get("coordinate2")
            return ActionResult(
                action=data.get("action", "unknown"),
                coordinate=tuple(c1) if c1 else None,
                coordinate2=tuple(c2) if c2 else None,
                text=data.get("text"),
                time=data.get("time"),
                status=data.get("status"),
                description=data.get("description"),
            )
        except json.JSONDecodeError:
            pass
    
    # Fallback parsing for non-JSON format (key: value, key2: value2)
    try:
        data = {}
        # Remove braces if present but failed JSON parse
        clean_content = content.strip().strip("{}")
        parts = clean_content.split(", ")
        for part in parts:
            if ":" in part:
                k, v = part.split(":", 1)
                k = k.strip().strip('"\'')
                v = v.strip().strip('"\'')
                
                # Handle coordinates [x, y]
                if v.startswith("[") and v.endswith("]"):
                    try:
                        v = json.loads(v)
                    except:
                        pass
                elif v.lower() == "true": v = True
                elif v.lower() == "false": v = False
                elif v.replace(".", "", 1).isdigit(): v = float(v)
                
                data[k] = v
        
        c1 = data.get("coordinate")
        c2 = data.get("coordinate2")
        return ActionResult(
            action=data.get("action", "unknown"),
            coordinate=tuple(c1) if c1 else None,
            coordinate2=tuple(c2) if c2 else None,
            text=data.get("text"),
            time=data.get("time"),
            status=data.get("status"),
            description=data.get("description"),
        )
    except Exception:
        return ActionResult(action="error", status=f"Failed to parse: {content}")

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
