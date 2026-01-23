"""
Main Token Optimizer class.
Orchestrates compression and pruning strategies.
"""

import logging
from typing import List, Optional

from langchain_core.messages import BaseMessage

from .strategies import OptimizationStrategy, OptimizationConfig, OptimizationResult
from .compressor import compress_messages
from .pruner import prune_oldest_messages, prune_images, prune_duplicates

# Import token counter from utils
try:
    from src.utils.token_counter import count_messages_tokens
except ImportError:
    # Fallback if import fails
    def count_messages_tokens(messages):
        return sum(len(str(m.content)) // 4 for m in messages)

logger = logging.getLogger(__name__)


class TokenOptimizer:
    """
    Main Token Optimizer.
    
    Applies multi-stage optimization to reduce token count:
    1. Compression (whitespace, base64 removal)
    2. Tool result summarization
    3. Duplicate removal
    4. Image pruning
    5. Message pruning
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize optimizer.
        
        Args:
            config: Optimization config (uses defaults if None)
        """
        self.config = config or OptimizationConfig()
    
    def optimize(
        self,
        messages: List[BaseMessage],
        target_tokens: Optional[int] = None,
        strategy: Optional[OptimizationStrategy] = None,
    ) -> tuple[List[BaseMessage], OptimizationResult]:
        """
        Optimize messages to reduce token count.
        
        Args:
            messages: List of messages to optimize
            target_tokens: Target token count (uses config default if None)
            strategy: Strategy to use (uses config default if None)
            
        Returns:
            (optimized_messages, optimization_result)
        """
        target = target_tokens or self.config.target_tokens
        strat = strategy or self.config.strategy
        
        # Get strategy-specific config
        config = self.config.for_strategy(strat)
        
        # Count original tokens
        original_tokens = count_messages_tokens(messages)
        
        # If under target with ADAPTIVE, skip optimization
        if strat == OptimizationStrategy.ADAPTIVE and original_tokens <= target:
            return messages, OptimizationResult(
                original_tokens=original_tokens,
                optimized_tokens=original_tokens,
                tokens_saved=0,
                messages_pruned=0,
                images_removed=0,
                strategy_used=strat,
            )
        
        # NONE strategy: return as-is
        if strat == OptimizationStrategy.NONE:
            return messages, OptimizationResult(
                original_tokens=original_tokens,
                optimized_tokens=original_tokens,
                tokens_saved=0,
                messages_pruned=0,
                images_removed=0,
                strategy_used=strat,
            )
        
        # Apply optimizations
        optimized = list(messages)
        messages_pruned = 0
        images_removed = 0
        
        # Stage 1: Compression
        compress_config = {
            "compress_whitespace": config.compress_whitespace,
            "max_tool_result_chars": config.max_tool_result_chars,
            "summarize_tool_results": config.summarize_tool_results,
            "remove_base64": strat == OptimizationStrategy.AGGRESSIVE,
        }
        optimized = compress_messages(optimized, compress_config)
        
        # Stage 2: Remove duplicates
        if config.remove_duplicates:
            optimized, dups_removed = prune_duplicates(optimized)
            messages_pruned += dups_removed
        
        # Stage 3: Prune images
        if config.strip_old_images:
            optimized, imgs_removed = prune_images(optimized, config.max_images)
            images_removed = imgs_removed
        
        # Stage 4: Check if we need more pruning
        current_tokens = count_messages_tokens(optimized)
        
        if current_tokens > target and strat in [OptimizationStrategy.AGGRESSIVE, OptimizationStrategy.ADAPTIVE]:
            # Calculate how many messages to prune
            # Rough estimate: average tokens per message
            avg_per_msg = current_tokens / len(optimized) if optimized else 100
            msgs_to_remove = int((current_tokens - target) / avg_per_msg) + 1
            
            target_count = max(config.min_messages_keep, len(optimized) - msgs_to_remove)
            
            optimized, pruned = prune_oldest_messages(
                optimized,
                target_count=target_count,
                preserve_essential=True,
            )
            messages_pruned += pruned
        
        # Final token count
        optimized_tokens = count_messages_tokens(optimized)
        
        result = OptimizationResult(
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            tokens_saved=original_tokens - optimized_tokens,
            messages_pruned=messages_pruned,
            images_removed=images_removed,
            strategy_used=strat,
        )
        
        logger.info(f"Token optimization: {result}")
        
        return optimized, result
    
    def estimate_savings(self, messages: List[BaseMessage]) -> dict:
        """
        Estimate potential savings without actually optimizing.
        
        Returns:
            Dict with estimates for each strategy
        """
        original = count_messages_tokens(messages)
        
        estimates = {}
        
        for strat in OptimizationStrategy:
            if strat == OptimizationStrategy.NONE:
                estimates[strat.name] = {"tokens": original, "savings": 0}
            else:
                # Run optimization in "dry run" mode
                _, result = self.optimize(
                    messages,
                    strategy=strat,
                )
                estimates[strat.name] = {
                    "tokens": result.optimized_tokens,
                    "savings": result.tokens_saved,
                    "savings_percent": result.savings_percent,
                }
        
        return estimates
    
    def auto_select_strategy(self, messages: List[BaseMessage]) -> OptimizationStrategy:
        """
        Automatically select best strategy based on current context.
        
        Returns:
            Recommended strategy
        """
        tokens = count_messages_tokens(messages)
        
        if tokens < self.config.target_tokens * 0.5:
            return OptimizationStrategy.NONE
        elif tokens < self.config.target_tokens:
            return OptimizationStrategy.LIGHT
        elif tokens < self.config.max_tokens:
            return OptimizationStrategy.AGGRESSIVE
        else:
            return OptimizationStrategy.AGGRESSIVE
