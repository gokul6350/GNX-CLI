"""Token counter for tracking model usage and costs."""
from langchain_core.messages import BaseMessage
from typing import Dict, List, Union

# Approximate token counts per character (varies by model)
# Gemma-3-27b uses similar tokenization to other modern LLMs
TOKENS_PER_CHAR = 0.25  # ~4 chars per token average

def count_tokens_approximate(text: str) -> int:
    """
    Approximate token count for text.
    More accurate than character count but doesn't require tokenizer.
    """
    if not text:
        return 0
    # Average English: ~4 characters per token
    return max(1, int(len(text) * TOKENS_PER_CHAR))

def count_message_tokens(message: BaseMessage) -> int:
    """Count tokens in a single message."""
    return count_tokens_approximate(str(message.content))

def count_messages_tokens(messages: List[BaseMessage]) -> int:
    """Count total tokens in a list of messages."""
    total = 0
    for msg in messages:
        total += count_message_tokens(msg)
        # Add overhead per message for formatting
        total += 4
    return total

def format_token_stats(input_tokens: int, output_tokens: int = 0) -> Dict:
    """Format token statistics with costs (Gemma-3-27b pricing via DeepInfra)."""
    total_tokens = input_tokens + output_tokens
    
    # Gemma-3-27b pricing via DeepInfra
    # Input: $0.09/1M tokens, Output: $0.17/1M tokens
    input_cost = (input_tokens / 1_000_000) * 0.09
    output_cost = (output_tokens / 1_000_000) * 0.17
    total_cost = input_cost + output_cost
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost": f"${input_cost:.6f}",
        "output_cost": f"${output_cost:.6f}",
        "total_cost": f"${total_cost:.6f}",
    }

def create_token_report(messages: List[BaseMessage], session_label: str = "Session") -> str:
    """Create a readable token usage report."""
    input_tokens = count_messages_tokens(messages)
    stats = format_token_stats(input_tokens)
    
    report = f"""
╭──────────────────────────────────────────────────╮
│         {session_label} Token Usage Report          │
╰──────────────────────────────────────────────────╯

Input Tokens:    {stats['input_tokens']:,}
Output Tokens:   {stats['output_tokens']:,}
Total Tokens:    {stats['total_tokens']:,}

Input Cost:      {stats['input_cost']}
Output Cost:     {stats['output_cost']}
Total Cost:      {stats['total_cost']}

Messages:        {len(messages)}
Avg per message: {input_tokens // len(messages) if messages else 0} tokens
"""
    return report
