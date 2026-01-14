"""
Configuration loading for Vision Client.
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Try to import config, handle if not found
try:
    import config
except ImportError:
    config = None

load_dotenv(override=True)

# Default Configuration
DEFAULT_HF_BASE_URL = "https://router.huggingface.co/v1"
DEFAULT_V_ACTION_MODEL = "Qwen/Qwen3-VL-4B-Instruct:fastest"


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
        
        # Check for Novita-specific key
        if api_key == "novita" or "novita" in str(base_url).lower():
            novita_key = os.environ.get("NOVITA_API_KEY")
            if novita_key:
                api_key = novita_key
            
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
