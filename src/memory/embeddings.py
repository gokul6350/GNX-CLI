"""
Embedding generation for semantic memory retrieval.
Supports mock embeddings and optional real providers.
"""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file so API keys are available
load_dotenv()


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Hash-based mock embedding provider.
    Generates deterministic pseudo-embeddings without external API calls.
    Useful for testing and zero-dependency operation.
    """
    
    def __init__(self, dimension: int = 128):
        self._dimension = dimension
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def embed(self, text: str) -> List[float]:
        """Generate a deterministic pseudo-embedding from text hash."""
        # Use SHA256 for deterministic hashing
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Convert bytes to floats in range [-1, 1]
        embedding = []
        for i in range(self._dimension):
            # Use modulo to cycle through hash bytes
            byte_idx = i % len(hash_bytes)
            # Normalize to [-1, 1]
            value = (hash_bytes[byte_idx] / 127.5) - 1.0
            embedding.append(value)
        
        # Normalize to unit vector
        return self._normalize(embedding)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]
    
    def _normalize(self, vec: List[float]) -> List[float]:
        """Normalize vector to unit length."""
        magnitude = math.sqrt(sum(x * x for x in vec))
        if magnitude == 0:
            return vec
        return [x / magnitude for x in vec]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-small.
    Requires OPENAI_API_KEY environment variable.
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._dimension = 1536  # Default for text-embedding-3-small
        self._client = None
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI()
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Gemini embedding provider using gemini-embedding-001.
    Requires GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
    """
    
    def __init__(self, model: str = "gemini-embedding-001"):
        self.model = model
        self._dimension = 768  # Gemini embedding dimension
        self._client = None
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client()
            except ImportError:
                raise ImportError("google-genai package required. Install with: pip install google-genai")
        return self._client
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding using Gemini API."""
        client = self._get_client()
        result = client.models.embed_content(
            model=self.model,
            contents=[text]
        )
        return list(result.embeddings[0].values)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        client = self._get_client()
        result = client.models.embed_content(
            model=self.model,
            contents=texts
        )
        return [list(emb.values) for emb in result.embeddings]


class EmbeddingManager:
    """
    Factory for embedding providers.
    Auto-selects based on available dependencies.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize embedding manager.
        
        Args:
            provider: "mock", "openai", "gemini", or None for auto-detect
        """
        self.provider_name = provider or self._auto_detect()
        self.provider = self._create_provider()
    
    def _auto_detect(self) -> str:
        """Auto-detect best available provider."""
        import os
        
        # Check for Gemini API key first (preferred)
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            try:
                from google import genai
                return "gemini"
            except ImportError:
                pass
        
        # Check for OpenAI API key
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                return "openai"
            except ImportError:
                pass
        
        # Fallback to mock
        return "mock"
    
    def _create_provider(self) -> EmbeddingProvider:
        """Create the embedding provider instance."""
        if self.provider_name == "gemini":
            return GeminiEmbeddingProvider()
        elif self.provider_name == "openai":
            return OpenAIEmbeddingProvider()
        else:
            return MockEmbeddingProvider()
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self.provider.embed(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.provider.embed_batch(texts)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.provider.dimension
