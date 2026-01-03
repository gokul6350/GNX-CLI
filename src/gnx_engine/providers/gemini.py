from langchain_google_genai import ChatGoogleGenerativeAI

GEMINI_CONFIG = {
    "default_model": "gemma-3-27b-it",
    "env_key": "GOOGLE_API_KEY",
    "models": ["gemma-3-27b-it", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
}

def create_gemini_llm(model_name: str, temperature: float = 0.7):
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
    )
