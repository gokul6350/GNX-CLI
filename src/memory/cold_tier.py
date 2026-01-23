"""
Cold Tier - Persistent disk storage for archived memories.
"""

import os
import json
import time
import logging
from typing import List, Optional
from pathlib import Path

from .types import MemoryCube, MemoryTier
from .analytics import MemoryAnalytics

logger = logging.getLogger(__name__)


class ColdTier:
    """
    Cold Tier Memory Manager.
    
    Stores archived memories on disk as JSON files.
    Used for rarely accessed memories that should persist long-term.
    """
    
    DEFAULT_PATH = os.path.expanduser("~/.gnx/cold_memory")
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        analytics: Optional[MemoryAnalytics] = None,
    ):
        """
        Initialize Cold Tier.
        
        Args:
            storage_path: Path to storage directory
            analytics: Optional analytics tracker
        """
        self.storage_path = Path(storage_path or self.DEFAULT_PATH)
        self.analytics = analytics
        self._cache: List[MemoryCube] = []  # In-memory cache of cold memories
        
        # Ensure directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cold Tier initialized at {self.storage_path}")
    
    def _get_archive_file(self) -> Path:
        """Get path to the main archive file."""
        return self.storage_path / "archive.json"
    
    def save(self, memories: List[MemoryCube]):
        """
        Save memories to cold storage.
        
        Args:
            memories: List of MemoryCubes to archive
        """
        # Load existing archive
        existing = self._load_archive()
        
        # Add new memories (update tier)
        for mem in memories:
            mem.tier = MemoryTier.COLD
            existing.append(mem)
        
        # Save back
        self._save_archive(existing)
        
        # Update cache
        self._cache = existing
        
        logger.info(f"Archived {len(memories)} memories to cold storage")
    
    def _load_archive(self) -> List[MemoryCube]:
        """Load archive from disk."""
        archive_file = self._get_archive_file()
        
        if not archive_file.exists():
            return []
        
        try:
            with open(archive_file, "r") as f:
                data = json.load(f)
            
            return [MemoryCube.from_dict(item) for item in data]
        except Exception as e:
            logger.error(f"Error loading cold archive: {e}")
            return []
    
    def _save_archive(self, memories: List[MemoryCube]):
        """Save archive to disk."""
        archive_file = self._get_archive_file()
        
        try:
            data = [mem.to_dict() for mem in memories]
            with open(archive_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cold archive: {e}")
    
    def search(self, query: str, k: int = 3) -> List[MemoryCube]:
        """
        Search cold storage (basic text matching).
        
        Note: Cold tier uses simple text matching, not semantic search.
        For semantic search, rehydrate to warm tier first.
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of matching MemoryCubes
        """
        start_time = time.perf_counter()
        
        # Load if cache is empty
        if not self._cache:
            self._cache = self._load_archive()
        
        # Simple text matching
        query_lower = query.lower()
        matches = []
        
        for mem in self._cache:
            if query_lower in mem.content.lower():
                matches.append(mem)
                mem.update_access()
        
        # Sort by relevance (simple: more matches = better)
        matches.sort(key=lambda m: m.content.lower().count(query_lower), reverse=True)
        results = matches[:k]
        
        # Log timing
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        if self.analytics:
            self.analytics.log_retrieval(
                query=query,
                tier="COLD",
                retrieval_time_ms=elapsed_ms,
                results_count=len(results),
                candidates_searched=len(self._cache),
            )
        
        return results
    
    def rehydrate(self, memory_id: str) -> Optional[MemoryCube]:
        """
        Retrieve a memory from cold storage for rehydration to warm tier.
        
        Args:
            memory_id: ID of memory to retrieve
            
        Returns:
            MemoryCube if found, None otherwise
        """
        if not self._cache:
            self._cache = self._load_archive()
        
        for mem in self._cache:
            if mem.id == memory_id:
                return mem
        
        return None
    
    def remove(self, memory_id: str) -> bool:
        """Remove a memory from cold storage."""
        if not self._cache:
            self._cache = self._load_archive()
        
        for i, mem in enumerate(self._cache):
            if mem.id == memory_id:
                del self._cache[i]
                self._save_archive(self._cache)
                return True
        
        return False
    
    def get_all(self) -> List[MemoryCube]:
        """Get all cold memories."""
        if not self._cache:
            self._cache = self._load_archive()
        return list(self._cache)
    
    def size(self) -> int:
        """Return number of cold memories."""
        if not self._cache:
            self._cache = self._load_archive()
        return len(self._cache)
    
    def clear(self):
        """Clear all cold storage."""
        self._cache.clear()
        archive_file = self._get_archive_file()
        if archive_file.exists():
            archive_file.unlink()
