"""
Vector similarity search for semantic memory retrieval.
"""

import math
from typing import List, Tuple, Optional

from .types import MemoryCube


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns value in range [-1, 1], where 1 is most similar.
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate Euclidean distance between two vectors."""
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
    
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))


class VectorIndex:
    """
    In-memory vector index for k-NN search.
    Stores MemoryCubes and provides similarity search.
    """
    
    def __init__(self):
        self._items: List[MemoryCube] = []
    
    def add(self, cube: MemoryCube):
        """Add a memory cube to the index."""
        self._items.append(cube)
    
    def add_batch(self, cubes: List[MemoryCube]):
        """Add multiple memory cubes."""
        self._items.extend(cubes)
    
    def remove(self, cube_id: str) -> bool:
        """Remove a cube by ID. Returns True if found and removed."""
        for i, cube in enumerate(self._items):
            if cube.id == cube_id:
                del self._items[i]
                return True
        return False
    
    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Tuple[MemoryCube, float]]:
        """
        Search for k most similar memories.
        
        Args:
            query_vector: Query embedding
            k: Number of results
            threshold: Minimum similarity score (optional)
            
        Returns:
            List of (MemoryCube, similarity_score) tuples, sorted by score descending
        """
        if not self._items:
            return []
        
        # Calculate similarities
        scored = []
        for cube in self._items:
            score = cosine_similarity(query_vector, cube.embedding)
            if threshold is None or score >= threshold:
                scored.append((cube, score))
        
        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[:k]
    
    def search_with_heat(
        self,
        query_vector: List[float],
        k: int = 5,
        heat_weight: float = 0.3,
    ) -> List[Tuple[MemoryCube, float]]:
        """
        Search combining similarity with heat score.
        
        Args:
            query_vector: Query embedding
            k: Number of results
            heat_weight: Weight for heat score (0-1), rest for similarity
            
        Returns:
            List of (MemoryCube, combined_score) tuples
        """
        if not self._items:
            return []
        
        # Get max heat for normalization
        max_heat = max((cube.heat_score() for cube in self._items), default=1.0)
        if max_heat == 0:
            max_heat = 1.0
        
        scored = []
        for cube in self._items:
            similarity = cosine_similarity(query_vector, cube.embedding)
            normalized_heat = cube.heat_score() / max_heat
            
            # Combined score
            combined = (1 - heat_weight) * similarity + heat_weight * normalized_heat
            scored.append((cube, combined))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
    
    def get_by_id(self, cube_id: str) -> Optional[MemoryCube]:
        """Get a cube by its ID."""
        for cube in self._items:
            if cube.id == cube_id:
                return cube
        return None
    
    def get_all(self) -> List[MemoryCube]:
        """Get all cubes in the index."""
        return list(self._items)
    
    def size(self) -> int:
        """Return number of items in index."""
        return len(self._items)
    
    def clear(self):
        """Clear all items from index."""
        self._items.clear()
