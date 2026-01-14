from .gemini import GEMINI_CONFIG, create_gemini_llm
from .glm import GLM_CONFIG, create_glm_llm
from .groq import GROQ_CONFIG, create_groq_llm

# Groq with Llama 4 Scout is the primary/default provider
PROVIDERS = {
    "glm": {
        **GLM_CONFIG,
        "factory": create_glm_llm,
    },
    "groq": {
        **GROQ_CONFIG,
        "factory": create_groq_llm,
    },
    "gemini": {
        **GEMINI_CONFIG,
        "factory": create_gemini_llm,
    },
}

def create_llm(provider_name: str, model_name: str, temperature: float = 0.7):
    provider = PROVIDERS.get(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")
    return provider["factory"](model_name, temperature)
