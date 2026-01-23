"""
Core data types for the Memory Operating System.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class MemoryTier(Enum):
    """
    Defines the 'velocity' of the memory.
    
    HOT:  Currently inside the LLM's Context Window (Fastest).
    WARM: Stored in Vector DB, retrieved via Semantic Search (Fast).
    COLD: Archived on disk, retrieved rarely (Slow).
    """
    HOT = 0
    WARM = 1
    COLD = 2


@dataclass
class MemoryCube:
    """
    The fundamental unit of Long-Term Memory.
    Wraps raw text with metadata for efficient retrieval.
    """
    id: str
    content: str
    timestamp: float
    embedding: List[float]
    tier: MemoryTier
    
    # Metadata for the 'Heat' Algorithm
    access_count: int = 0
    last_access: float = 0.0
    source_summary: bool = False
    
    # Optional metadata
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None
    
    def update_access(self):
        """Update access metrics when this memory is retrieved."""
        self.access_count += 1
        self.last_access = time.time()
    
    def heat_score(self) -> float:
        """
        Calculate heat score based on access frequency and recency.
        Higher score = more "hot" memory.
        """
        if self.access_count == 0:
            return 0.0
        
        # Decay factor based on time since last access
        time_decay = 1.0 / (1.0 + (time.time() - self.last_access) / 3600)  # Hour-based decay
        
        # Combine access count with recency
        return self.access_count * time_decay
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp,
            "embedding": self.embedding,
            "tier": self.tier.name,
            "access_count": self.access_count,
            "last_access": self.last_access,
            "source_summary": self.source_summary,
            "tags": self.tags,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryCube":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=data["timestamp"],
            embedding=data["embedding"],
            tier=MemoryTier[data["tier"]],
            access_count=data.get("access_count", 0),
            last_access=data.get("last_access", 0.0),
            source_summary=data.get("source_summary", False),
            tags=data.get("tags", []),
            source=data.get("source"),
        )


@dataclass 
class RetrievalResult:
    """Result from a memory retrieval operation."""
    memories: List[MemoryCube]
    query: str
    retrieval_time_ms: float
    tier_source: MemoryTier
    total_candidates: int
    
    def __str__(self) -> str:
        return (
            f"Retrieved {len(self.memories)} memories from {self.tier_source.name} tier "
            f"in {self.retrieval_time_ms:.2f}ms (searched {self.total_candidates} candidates)"
        )
