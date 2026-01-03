"""
Image utilities for GNX CLI.
Handles image token estimation, validation, and processing.
"""
import base64
import re
from typing import Dict, Optional, Tuple
from .debug_logger import debug

# Groq Llama 4 Scout image limits
MAX_IMAGE_SIZE_URL = 20 * 1024 * 1024  # 20MB for URL
MAX_IMAGE_SIZE_BASE64 = 4 * 1024 * 1024  # 4MB for base64
MAX_RESOLUTION = 33_177_600  # 33 megapixels
MAX_IMAGES_PER_REQUEST = 5

# Token estimation for images
# Based on typical vision model token usage
# Small images (~256x256): ~200-400 tokens
# Medium images (~512x512): ~600-1000 tokens
# Large images (~1024x1024): ~1500-2500 tokens
# Very large images: ~3000-5000 tokens
IMAGE_TOKEN_ESTIMATES = {
    "tiny": 200,      # < 128x128
    "small": 400,     # 128x128 - 256x256
    "medium": 800,    # 256x256 - 512x512
    "large": 1500,    # 512x512 - 1024x1024
    "xlarge": 2500,   # 1024x1024 - 2048x2048
    "xxlarge": 4000,  # > 2048x2048
}

# Default token estimate when we can't determine size
DEFAULT_IMAGE_TOKENS = 1000


def estimate_image_size_from_base64(data_url: str) -> Tuple[int, str]:
    """
    Estimate image size category from base64 data URL.
    Returns (estimated_tokens, size_category)
    """
    if not data_url:
        return DEFAULT_IMAGE_TOKENS, "unknown"
    
    # Extract base64 data
    if data_url.startswith("data:"):
        # Format: data:image/png;base64,XXXXXX
        match = re.match(r"data:image/[^;]+;base64,(.+)", data_url)
        if match:
            b64_data = match.group(1)
        else:
            return DEFAULT_IMAGE_TOKENS, "unknown"
    else:
        # Assume it's a URL, not base64
        return DEFAULT_IMAGE_TOKENS, "url"
    
    # Calculate approximate image size from base64 length
    # Base64 encoding increases size by ~33%
    # So original_size ≈ base64_length * 0.75
    b64_length = len(b64_data)
    approx_bytes = int(b64_length * 0.75)
    
    debug.image(f"Base64 analysis", {
        "b64_length": f"{b64_length:,} chars",
        "approx_bytes": f"{approx_bytes:,} bytes ({approx_bytes / 1024:.1f} KB)",
    })
    
    # Estimate resolution from file size
    # JPEG compression ratio is typically 10:1 to 20:1
    # PNG is lossless, typically 2:1 to 4:1
    # Assume average 8:1 compression for estimation
    approx_pixels = approx_bytes * 8 / 3  # RGB = 3 bytes per pixel
    approx_side = int(approx_pixels ** 0.5)  # Assume square
    
    debug.image(f"Estimated resolution", {
        "approx_pixels": f"{int(approx_pixels):,}",
        "approx_dimensions": f"~{approx_side}x{approx_side}",
    })
    
    # Categorize by estimated resolution
    if approx_side < 128:
        return IMAGE_TOKEN_ESTIMATES["tiny"], "tiny"
    elif approx_side < 256:
        return IMAGE_TOKEN_ESTIMATES["small"], "small"
    elif approx_side < 512:
        return IMAGE_TOKEN_ESTIMATES["medium"], "medium"
    elif approx_side < 1024:
        return IMAGE_TOKEN_ESTIMATES["large"], "large"
    elif approx_side < 2048:
        return IMAGE_TOKEN_ESTIMATES["xlarge"], "xlarge"
    else:
        return IMAGE_TOKEN_ESTIMATES["xxlarge"], "xxlarge"


def estimate_image_tokens(image_content: Dict) -> int:
    """
    Estimate token count for an image content dict.
    
    Args:
        image_content: Dict with type="image_url" and image_url.url
        
    Returns:
        Estimated token count for the image
    """
    if not isinstance(image_content, dict):
        return 0
    
    if image_content.get("type") != "image_url":
        return 0
    
    image_url_data = image_content.get("image_url", {})
    url = image_url_data.get("url", "") if isinstance(image_url_data, dict) else ""
    
    if not url:
        return 0
    
    # Check if it's a data URL (base64) or regular URL
    if url.startswith("data:image"):
        tokens, category = estimate_image_size_from_base64(url)
        debug.image(f"Image token estimate: {tokens} ({category})")
        return tokens
    else:
        # Regular URL - use default estimate
        debug.image(f"Image URL detected, using default estimate: {DEFAULT_IMAGE_TOKENS}")
        return DEFAULT_IMAGE_TOKENS


def validate_image_for_groq(data_url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an image against Groq's limits.
    
    Returns:
        (is_valid, error_message)
    """
    if not data_url:
        return False, "Empty image data"
    
    if data_url.startswith("data:image"):
        # Base64 image
        match = re.match(r"data:image/[^;]+;base64,(.+)", data_url)
        if not match:
            return False, "Invalid base64 data URL format"
        
        b64_data = match.group(1)
        size_bytes = len(b64_data) * 0.75
        
        if size_bytes > MAX_IMAGE_SIZE_BASE64:
            return False, f"Image too large: {size_bytes/1024/1024:.1f}MB > 4MB limit"
    else:
        # URL - can't validate size without fetching
        pass
    
    return True, None


def get_image_info(data_url: str) -> Dict:
    """Get information about an image from its data URL."""
    info = {
        "type": "unknown",
        "size_bytes": 0,
        "estimated_tokens": DEFAULT_IMAGE_TOKENS,
        "size_category": "unknown",
        "valid": False,
        "error": None,
    }
    
    if not data_url:
        info["error"] = "Empty data URL"
        return info
    
    if data_url.startswith("data:image"):
        info["type"] = "base64"
        
        # Extract format
        format_match = re.match(r"data:image/([^;]+);base64,", data_url)
        if format_match:
            info["format"] = format_match.group(1)
        
        # Get size
        match = re.match(r"data:image/[^;]+;base64,(.+)", data_url)
        if match:
            b64_data = match.group(1)
            info["size_bytes"] = int(len(b64_data) * 0.75)
        
        # Get token estimate
        info["estimated_tokens"], info["size_category"] = estimate_image_size_from_base64(data_url)
    else:
        info["type"] = "url"
        info["url"] = data_url[:100] + "..." if len(data_url) > 100 else data_url
        info["estimated_tokens"] = DEFAULT_IMAGE_TOKENS
    
    # Validate
    info["valid"], info["error"] = validate_image_for_groq(data_url)
    
    return info
