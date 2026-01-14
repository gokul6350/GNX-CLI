"""
Vision Model Client - Generic interface to Vision-Language Models.
"""

import json
import logging
import time
import datetime
from typing import Optional

from openai import OpenAI

from .config import get_vl_config
from .types import ActionResult

logger = logging.getLogger(__name__)


def log_step(step_name: str, start_time: Optional[float] = None) -> float:
    """Log a step with optional duration."""
    current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if start_time:
        duration = time.time() - start_time
        print(f"[{current_time}] [COMPLETED] {step_name} (Took: {duration:.4f}s)")
    else:
        print(f"[{current_time}] [STARTED] {step_name}")
    return time.time()


class VisionModelClient:
    """Client for interacting with Vision-Language Models."""
    
    def __init__(self):
        self.config = get_vl_config()
        self.client = self._create_client()
        self.model = self.config["model"]
    
    def _create_client(self) -> OpenAI:
        """Create OpenAI client based on configuration."""
        conf = self.config
        
        if conf["provider"] == "huggingface":
            token = conf["api_key"]
            if not token:
                raise ValueError(
                    "HF_TOKEN not found in environment. "
                    "Please set HF_TOKEN in your .env file for Vision model. "
                    "Get a valid token from: https://huggingface.co/settings/tokens"
                )
            if token.startswith("your_") or len(token) < 10:
                raise ValueError(f"Invalid HF_TOKEN: '{token}'")
            
            return OpenAI(base_url=conf["base_url"], api_key=token)
        
        elif conf["provider"] == "custom":
            base_url = conf["base_url"]
            if not base_url:
                raise ValueError("VL_BASE_URL not set for custom provider.")
            
            # Ensure base_url format is correct
            if base_url.endswith("/chat/completions"):
                base_url = base_url.replace("/chat/completions", "")
            if base_url.endswith("/v1/"):
                base_url = base_url[:-1]
            elif not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            
            return OpenAI(base_url=base_url, api_key=conf["api_key"])
        
        raise ValueError(f"Unknown provider: {conf['provider']}")
    
    def query(
        self,
        system_prompt: str,
        user_text: str,
        image_data_url: str,
        temperature: float = 0.1,
        max_tokens: int = 200
    ) -> str:
        """
        Query the Vision-Language model with text and image.
        
        Args:
            system_prompt: System instructions for the model.
            user_text: User query/instruction.
            image_data_url: Base64 encoded image as data URL.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
        
        Returns:
            Raw model response text.
        """
        step_start = log_step("Query VL Model")
        
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
            
            # DEBUG: Save request payload
            try:
                debug_payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                with open("last_vl_request.json", "w", encoding="utf-8") as f:
                    json.dump(debug_payload, f, indent=2)
            except Exception:
                pass
            
            log_step(f"Sending request to {self.config.get('base_url')} (Model: {self.model})")
            req_start = time.time()
            
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            log_step("VL Model Request", req_start)
            log_step("Query VL Model", step_start)
            
            return resp.choices[0].message.content
        
        except Exception as e:
            error_msg = str(e)
            print(f"Error in query_vl_model: {error_msg}")
            
            if "401" in error_msg or "Unauthorized" in error_msg:
                if self.config["provider"] == "huggingface":
                    error_msg += "\nHint: Check your HF_TOKEN in .env file."
            
            log_step("Query VL Model (Failed)", step_start)
            raise


# Global client instance (lazy initialization)
_client: Optional[VisionModelClient] = None


def get_vision_client() -> VisionModelClient:
    """Get or create the global VisionModelClient instance."""
    global _client
    if _client is None:
        _client = VisionModelClient()
    return _client


def reset_vision_client():
    """Reset the cached client to force re-reading config."""
    global _client
    _client = None
