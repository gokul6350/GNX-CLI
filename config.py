DEBUG=False


# Vision-Language Provider Configuration
# Options: "huggingface" (default), "custom"
VL_PROVIDER = "custom"

# Custom Provider Settings (only used if VL_PROVIDER="custom")
# Example for local server or other API
VL_BASE_URL = "https://qwen3vl-2b-it-nexa.90xdev.dev"
VL_API_KEY = "dummy"
VL_MODEL = "NexaAI/Qwen3-VL-8B-Instruct-GGUF"#"NexaAI/Qwen3-VL-2B-Instruct-GGUF"  