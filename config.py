DEBUG=False

# Main AI Vision Support
# Set to False if your main AI (e.g., GLM) doesn't support images
# When False, screenshots won't be added to conversation - use activate_vision_agent instead
VISION_FOR_MAIN_AI = False


# Vision-Language Provider Configuration
# Options: "huggingface" (default), "custom"
VL_PROVIDER = "custom"

# Custom Provider Settings (only used if VL_PROVIDER="custom")
# Novita AI - OpenAI compatible endpoint
VL_BASE_URL = "https://api.novita.ai/openai/v1"
VL_API_KEY = "novita"  # Uses NOVITA_API_KEY from .env
VL_MODEL = "qwen/qwen3-vl-30b-a3b-instruct"
