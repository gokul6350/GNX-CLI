from langchain_groq import ChatGroq

GROQ_CONFIG = {
    "default_model": "meta-llama/llama-4-scout-17b-16e-instruct",
    "env_key": "GROQ_API_KEY",
    "models": [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ]
}

def create_groq_llm(model_name: str, temperature: float = 0.7):
    """Create a Groq LLM instance with native tool calling support."""
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_tokens=4096,  # Increased for longer responses, model has 128K context
    )
