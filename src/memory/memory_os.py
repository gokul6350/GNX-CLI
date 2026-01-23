"""
Advanced Memory Operating System.
Main orchestrator for Hot/Warm/Cold tier memory management.
"""

import time
import logging
from typing import List, Dict, Any, Optional

from langchain_core.language_models import BaseChatModel

from .types import MemoryCube, MemoryTier, RetrievalResult
from .hot_tier import HotTier
from .warm_tier import WarmTier
from .cold_tier import ColdTier
from .analytics import MemoryAnalytics

logger = logging.getLogger(__name__)


class AdvancedMemoryOS:
    """
    A Hybrid Memory Manager with 3-Tier Architecture.
    
    Tiers:
    - HOT: Active context window (managed by LangChain)
    - WARM: Long-term vector store (semantic retrieval)
    - COLD: Disk archive (persistent storage)
    
    Features:
    - Automatic Hot → Warm migration when context is summarized
    - Semantic search across Warm tier
    - Performance analytics with timing
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        max_token_limit: int = 12000,
        embedding_provider: str = None,  # None = auto-detect (gemini > openai > mock)
        enable_analytics: bool = True,
        cold_storage_path: Optional[str] = None,
    ):
        """
        Initialize the Memory OS.
        
        Args:
            llm: LangChain model for summarization (optional)
            max_token_limit: Token limit for hot tier
            embedding_provider: "gemini", "openai", "mock", or None for auto-detect
            enable_analytics: Enable performance logging
            cold_storage_path: Path for cold storage
        """
        # Analytics
        self.analytics = MemoryAnalytics(enable_live_logging=enable_analytics) if enable_analytics else None
        
        # Initialize tiers
        self.hot = HotTier(llm=llm, max_token_limit=max_token_limit)
        self.warm = WarmTier(embedding_provider=embedding_provider, analytics=self.analytics)
        self.cold = ColdTier(storage_path=cold_storage_path, analytics=self.analytics)
        
        logger.info(f"MemoryOS initialized (hot_limit={max_token_limit}, embeddings={embedding_provider})")
    
    # =========================================================================
    # CORE LIFECYCLE
    # =========================================================================
    
    def process_turn(self, user_input: str, ai_output: str):
        """
        Main lifecycle method. Call after every AI generation.
        
        1. Saves interaction to Hot tier
        2. Checks for new summaries
        3. Migrates summaries to Warm tier
        
        Args:
            user_input: User's message
            ai_output: AI's response
        """
        # 1. Save to Hot tier
        self.hot.add_turn(user_input, ai_output)
        
        # 2. Check for and migrate new summaries
        self._migrate_summaries()
    
    def _migrate_summaries(self):
        """Migrate new summaries from Hot to Warm tier."""
        summary = self.hot.consume_summary()
        
        if summary:
            logger.info("Hot tier summary detected, migrating to Warm tier...")
            self.add_memory(
                content=summary,
                source_summary=True,
                source="hot_tier_summary"
            )
    
    # =========================================================================
    # MEMORY OPERATIONS
    # =========================================================================
    
    def add_memory(
        self,
        content: str,
        source_summary: bool = False,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> MemoryCube:
        """
        Manually add a memory to the Warm tier.
        
        Args:
            content: Text content
            source_summary: True if from summarization
            tags: Optional tags
            source: Optional source identifier
            
        Returns:
            Created MemoryCube
        """
        return self.warm.add(
            content=content,
            source_summary=source_summary,
            tags=tags,
            source=source,
        )
    
    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        include_hot: bool = True,
        include_warm: bool = True,
        include_cold: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for the LLM.
        
        Args:
            query: Search query
            top_k: Results per tier
            include_hot: Include hot tier context
            include_warm: Search warm tier
            include_cold: Search cold tier
            
        Returns:
            Dict with context from each tier
        """
        result = {
            "hot_context": [],
            "warm_context": [],
            "cold_context": [],
            "total_time_ms": 0,
        }
        
        start = time.perf_counter()
        
        # Hot tier (always recent)
        if include_hot:
            result["hot_context"] = self.hot.get_context()
        
        # Warm tier (semantic search)
        if include_warm and self.warm.size() > 0:
            warm_memories = self.warm.search(query, k=top_k, use_heat=True)
            result["warm_context"] = [m.content for m in warm_memories]
        
        # Cold tier (disk search)
        if include_cold and self.cold.size() > 0:
            cold_memories = self.cold.search(query, k=top_k)
            result["cold_context"] = [m.content for m in cold_memories]
        
        result["total_time_ms"] = (time.perf_counter() - start) * 1000
        
        return result
    
    # =========================================================================
    # TIER MAINTENANCE
    # =========================================================================
    
    def archive_cold_memories(self):
        """Move cold memories from Warm to Cold tier."""
        candidates = self.warm.prune_cold()
        
        if candidates:
            # Remove from warm
            for mem in candidates:
                self.warm.remove(mem.id)
            
            # Add to cold
            self.cold.save(candidates)
            
            logger.info(f"Archived {len(candidates)} memories to cold storage")
    
    def rehydrate_memory(self, memory_id: str) -> Optional[MemoryCube]:
        """
        Bring a cold memory back to warm tier.
        
        Args:
            memory_id: ID of cold memory
            
        Returns:
            Rehydrated MemoryCube or None
        """
        cube = self.cold.rehydrate(memory_id)
        
        if cube:
            # Add back to warm
            cube.tier = MemoryTier.WARM
            self.warm.index.add(cube)
            
            # Remove from cold
            self.cold.remove(memory_id)
            
            logger.info(f"Rehydrated memory {memory_id} to warm tier")
            return cube
        
        return None
    
    # =========================================================================
    # STATS & DEBUG
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "hot_size": self.hot.size(),
            "warm_size": self.warm.size(),
            "cold_size": self.cold.size(),
            "total_memories": self.warm.size() + self.cold.size(),
        }
    
    def print_analytics(self):
        """Print performance analytics summary."""
        if self.analytics:
            self.analytics.print_summary()
    
    def clear_all(self):
        """Clear all tiers."""
        self.hot.clear()
        self.warm.clear()
        self.cold.clear()
        if self.analytics:
            self.analytics.reset()
