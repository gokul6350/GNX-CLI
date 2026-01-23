"""
Warm Tier - Long-term vector store for semantic retrieval.
"""

import time
import json
import os
import logging
from typing import List, Optional, Tuple
from pathlib import Path

from .types import MemoryCube, MemoryTier
from .vector_search import VectorIndex
from .embeddings import EmbeddingManager
from .analytics import MemoryAnalytics

logger = logging.getLogger(__name__)

DEFAULT_WARM_PATH = os.path.expanduser("~/.gnx/warm_memory.json")


class WarmTier:
    """
    Warm Tier Memory Manager.
    
    Stores memories as vectors for semantic retrieval.
    Persists to disk automatically.
    """
    
    def __init__(
        self,
        embedding_provider: str = None,  # None = auto-detect
        analytics: Optional[MemoryAnalytics] = None,
        storage_path: Optional[str] = None,
        auto_load: bool = True,
    ):
        """
        Initialize Warm Tier.
        
        Args:
            embedding_provider: "mock", "gemini", "openai", or None for auto-detect
            analytics: Optional analytics tracker
            storage_path: Path to persist memories (default: ~/.gnx/warm_memory.json)
            auto_load: Whether to load existing memories on init
        """
        self.storage_path = Path(storage_path or DEFAULT_WARM_PATH)
        self.embeddings = EmbeddingManager(provider=embedding_provider)
        self.index = VectorIndex()
        self.analytics = analytics
        self._id_counter = 0
        
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Auto-load existing memories
        if auto_load:
            self.load()
        
        logger.info(f"Warm Tier initialized with {self.embeddings.provider_name} embeddings")
    
    def _generate_id(self) -> str:
        """Generate unique memory ID."""
        self._id_counter += 1
        return f"mem_{int(time.time()*1000)}_{self._id_counter}"
    
    def add(
        self,
        content: str,
        source_summary: bool = False,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> MemoryCube:
        """Add a memory to the warm tier and save to disk."""
        # Generate embedding
        embedding = self.embeddings.embed(content)
        
        # Create cube
        cube = MemoryCube(
            id=self._generate_id(),
            content=content,
            timestamp=time.time(),
            embedding=embedding,
            tier=MemoryTier.WARM,
            source_summary=source_summary,
            tags=tags or [],
            source=source,
        )
        
        # Add to index
        self.index.add(cube)
        
        # Auto-save
        self.save()
        
        logger.debug(f"Added memory to Warm Tier: {cube.id}")
        return cube
    
    def search(
        self,
        query: str,
        k: int = 5,
        use_heat: bool = False,
        heat_weight: float = 0.3,
    ) -> List[MemoryCube]:
        """Search for relevant memories."""
        start_time = time.perf_counter()
        
        # Generate query embedding
        query_vector = self.embeddings.embed(query)
        
        # Search
        if use_heat:
            results = self.index.search_with_heat(query_vector, k, heat_weight)
        else:
            results = self.index.search(query_vector, k)
        
        # Update access metrics
        memories = []
        for cube, score in results:
            cube.update_access()
            memories.append(cube)
        
        # Log timing
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        if self.analytics:
            self.analytics.log_retrieval(
                query=query,
                tier="WARM",
                retrieval_time_ms=elapsed_ms,
                results_count=len(memories),
                candidates_searched=self.index.size(),
            )
        
        return memories
    
    def get_by_id(self, memory_id: str) -> Optional[MemoryCube]:
        """Get a memory by ID."""
        return self.index.get_by_id(memory_id)
    
    def remove(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        result = self.index.remove(memory_id)
        if result:
            self.save()
        return result
    
    def get_all(self) -> List[MemoryCube]:
        """Get all memories in warm tier."""
        return self.index.get_all()
    
    def size(self) -> int:
        """Return number of memories."""
        return self.index.size()
    
    def prune_cold(self, threshold: float = 0.1, max_age_hours: float = 24) -> List[MemoryCube]:
        """Identify memories that should be moved to cold tier."""
        cold_candidates = []
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        for cube in self.index.get_all():
            if cube.heat_score() < threshold and cube.last_access < cutoff_time:
                cold_candidates.append(cube)
        
        return cold_candidates
    
    def clear(self):
        """Clear all memories."""
        self.index.clear()
        self.save()
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def save(self):
        """Save all memories to disk."""
        try:
            data = [cube.to_dict() for cube in self.index.get_all()]
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(data)} memories to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save warm tier: {e}")
    
    def load(self):
        """Load memories from disk."""
        if not self.storage_path.exists():
            logger.debug(f"No existing warm tier at {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            for item in data:
                cube = MemoryCube.from_dict(item)
                self.index.add(cube)
                self._id_counter = max(self._id_counter, int(cube.id.split("_")[-1]) + 1)
            
            logger.info(f"Loaded {len(data)} memories from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load warm tier: {e}")
