"""
Optimization strategies for token management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OptimizationStrategy(Enum):
    """
    Token optimization strategy levels.
    
    NONE: No optimization (raw context)
    LIGHT: Minimal optimization (remove duplicates, trim whitespace)
    AGGRESSIVE: Heavy optimization (truncate, summarize tool outputs)
    ADAPTIVE: Dynamic based on context size
    """
    NONE = 0
    LIGHT = 1
    AGGRESSIVE = 2
    ADAPTIVE = 3


@dataclass
class OptimizationConfig:
    """Configuration for token optimization."""
    
    strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    
    # Target token limits
    target_tokens: int = 8000  # Target for optimization
    max_tokens: int = 12000   # Hard limit
    
    # Message retention
    min_messages_keep: int = 4      # Always keep last N messages
    max_tool_result_chars: int = 2000  # Truncate tool results beyond this
    
    # Image handling
    max_images: int = 3  # Max images in context
    strip_old_images: bool = True
    
    # Compression settings
    compress_whitespace: bool = True
    remove_duplicates: bool = True
    summarize_tool_results: bool = True
    
    def for_strategy(self, strategy: OptimizationStrategy) -> "OptimizationConfig":
        """Get config adjusted for specific strategy."""
        if strategy == OptimizationStrategy.NONE:
            return OptimizationConfig(
                strategy=strategy,
                target_tokens=self.max_tokens,
                compress_whitespace=False,
                remove_duplicates=False,
                summarize_tool_results=False,
            )
        elif strategy == OptimizationStrategy.LIGHT:
            return OptimizationConfig(
                strategy=strategy,
                target_tokens=self.max_tokens,
                max_tool_result_chars=5000,
                compress_whitespace=True,
                remove_duplicates=True,
                summarize_tool_results=False,
            )
        elif strategy == OptimizationStrategy.AGGRESSIVE:
            return OptimizationConfig(
                strategy=strategy,
                target_tokens=self.target_tokens,
                max_tool_result_chars=500,
                max_images=1,
                compress_whitespace=True,
                remove_duplicates=True,
                summarize_tool_results=True,
            )
        else:  # ADAPTIVE
            return self


@dataclass
class OptimizationResult:
    """Result of optimization operation."""
    
    original_tokens: int
    optimized_tokens: int
    tokens_saved: int
    messages_pruned: int
    images_removed: int
    strategy_used: OptimizationStrategy
    
    @property
    def savings_percent(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return (self.tokens_saved / self.original_tokens) * 100
    
    def __str__(self) -> str:
        return (
            f"Optimized: {self.original_tokens} → {self.optimized_tokens} tokens "
            f"({self.savings_percent:.1f}% saved, {self.messages_pruned} msgs pruned)"
        )
