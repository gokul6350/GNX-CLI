"""Token counter for tracking model usage and costs."""
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from typing import Dict, List, Union

# Import debug logger and image utils
from .debug_logger import debug
from .image_utils import estimate_image_tokens, get_image_info

# Approximate token counts per character (varies by model)
# Llama 4 Scout uses similar tokenization to other modern LLMs
TOKENS_PER_CHAR = 0.25  # ~4 chars per token average

# Message overhead tokens (for role markers, formatting)
MESSAGE_OVERHEAD = 4


def count_tokens_approximate(text: str) -> int:
    """
    Approximate token count for text.
    More accurate than character count but doesn't require tokenizer.
    """
    if not text:
        return 0
    # Average English: ~4 characters per token
    return max(1, int(len(text) * TOKENS_PER_CHAR))


def count_content_tokens(content) -> int:
    """
    Count tokens in message content, handling multimodal content properly.
    
    Args:
        content: String or list of content parts (text/image)
        
    Returns:
        Token count
    """
    if content is None:
        return 0
    
    # Simple string content
    if isinstance(content, str):
        tokens = count_tokens_approximate(content)
        debug.token(f"Text content: {tokens} tokens ({len(content)} chars)")
        return tokens
    
    # Multimodal content (list of parts)
    if isinstance(content, list):
        total = 0
        text_parts = 0
        image_parts = 0
        
        for part in content:
            if isinstance(part, dict):
                part_type = part.get("type", "")
                
                if part_type == "text":
                    text = part.get("text", "")
                    tokens = count_tokens_approximate(text)
                    total += tokens
                    text_parts += 1
                    debug.token(f"  Text part: {tokens} tokens")
                    
                elif part_type == "image_url":
                    # Use proper image token estimation - NOT counting base64 as text!
                    tokens = estimate_image_tokens(part)
                    total += tokens
                    image_parts += 1
                    
                    # Log detailed image info in debug mode
                    image_url = part.get("image_url", {})
                    url = image_url.get("url", "") if isinstance(image_url, dict) else ""
                    if url:
                        info = get_image_info(url)
                        debug.image(f"  Image part: {tokens} tokens", {
                            "type": info.get("type"),
                            "size": f"{info.get('size_bytes', 0) / 1024:.1f} KB",
                            "category": info.get("size_category"),
                        })
                else:
                    # Unknown part type, estimate from short repr
                    text_repr = str(part)[:200]  # Only use short repr
                    tokens = count_tokens_approximate(text_repr)
                    total += tokens
                    debug.token(f"  Unknown part ({part_type}): {tokens} tokens")
                    
            elif isinstance(part, str):
                tokens = count_tokens_approximate(part)
                total += tokens
                text_parts += 1
        
        debug.token(f"Multimodal content total: {total} tokens ({text_parts} text, {image_parts} images)")
        return total
    
    # Fallback: convert to string but limit length
    text_repr = str(content)[:1000]
    tokens = count_tokens_approximate(text_repr)
    debug.token(f"Fallback content: {tokens} tokens")
    return tokens


def count_message_tokens(message: BaseMessage) -> int:
    """Count tokens in a single message, including all content types."""
    msg_type = type(message).__name__
    
    # Get content tokens
    content_tokens = count_content_tokens(message.content)
    
    # Add message overhead
    total = content_tokens + MESSAGE_OVERHEAD
    
    # Additional tokens for tool messages
    if isinstance(message, ToolMessage):
        # Tool name and call ID add some overhead
        tool_name = getattr(message, 'name', '')
        if tool_name:
            total += count_tokens_approximate(tool_name)
    
    # AIMessage with tool_calls
    if isinstance(message, AIMessage):
        tool_calls = getattr(message, 'tool_calls', None)
        if tool_calls:
            for tc in tool_calls:
                # Count tool call structure
                total += count_tokens_approximate(tc.get('name', ''))
                args = tc.get('args', {})
                if args:
                    total += count_tokens_approximate(str(args))
    
    debug.token(f"{msg_type}: {total} tokens (content={content_tokens}, overhead={MESSAGE_OVERHEAD})")
    return total


def count_messages_tokens(messages: List[BaseMessage]) -> int:
    """Count total tokens in a list of messages."""
    debug.section("Token Counting")
    
    total = 0
    text_messages = 0
    image_messages = 0
    tool_messages = 0
    
    for i, msg in enumerate(messages):
        debug.indent()
        msg_tokens = count_message_tokens(msg)
        total += msg_tokens
        debug.dedent()
        
        # Track message types
        if isinstance(msg, ToolMessage):
            tool_messages += 1
        elif isinstance(msg.content, list):
            # Check if contains images
            has_image = any(
                isinstance(p, dict) and p.get("type") == "image_url" 
                for p in msg.content
            )
            if has_image:
                image_messages += 1
            else:
                text_messages += 1
        else:
            text_messages += 1
    
    debug.token(f"TOTAL: {total} tokens", {
        "messages": len(messages),
        "text_msgs": text_messages,
        "image_msgs": image_messages,
        "tool_msgs": tool_messages,
    })
    
    return total


def format_token_stats(input_tokens: int, output_tokens: int = 0) -> Dict:
    """Format token statistics with costs (Llama 4 Scout pricing via Groq)."""
    total_tokens = input_tokens + output_tokens
    
    # Groq Llama 4 Scout pricing (as of 2025)
    # See: https://console.groq.com/docs/models
    # Input: ~$0.11/1M tokens, Output: ~$0.34/1M tokens (approximate)
    input_cost = (input_tokens / 1_000_000) * 0.11
    output_cost = (output_tokens / 1_000_000) * 0.34
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
+--------------------------------------------------+
|         {session_label} Token Usage Report          |
+--------------------------------------------------+

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
