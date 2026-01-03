from .gemini import GEMINI_CONFIG, create_gemini_llm
from .groq import GROQ_CONFIG, create_groq_llm

PROVIDERS = {
    "gemini": {
        **GEMINI_CONFIG,
        "factory": create_gemini_llm
    },
    "groq": {
        **GROQ_CONFIG,
        "factory": create_groq_llm
    }
}

def create_llm(provider_name: str, model_name: str, temperature: float = 0.7):
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider["factory"](model_name, temperature)
