"""
Message compression utilities for token optimization.
"""

import re
import json
from typing import List, Tuple

from langchain_core.messages import BaseMessage, ToolMessage, AIMessage, HumanMessage


def compress_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple spaces/tabs with single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines)


def truncate_text(text: str, max_chars: int, suffix: str = "...[truncated]") -> str:
    """Truncate text to max characters with suffix."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def summarize_tool_result(result: str, max_chars: int = 500) -> str:
    """
    Summarize a tool result to reduce token usage.
    Extracts key information and truncates the rest.
    """
    # Try to parse as JSON for smarter summarization
    try:
        data = json.loads(result)
        
        # Handle screenshot results
        if isinstance(data, dict):
            if data.get("type") == "screenshot":
                return json.dumps({
                    "type": "screenshot",
                    "path": data.get("path"),
                    "dimensions": f"{data.get('width', '?')}x{data.get('height', '?')}",
                    # Remove base64 data
                })
            
            # Handle file listings
            if isinstance(data.get("files"), list):
                files = data["files"]
                if len(files) > 10:
                    return json.dumps({
                        "files": files[:10],
                        "note": f"...and {len(files) - 10} more files"
                    })
        
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Default: truncate
    return truncate_text(result, max_chars)


def remove_base64_from_text(text: str) -> Tuple[str, int]:
    """
    Remove base64 encoded data from text.
    Returns (cleaned_text, bytes_removed).
    """
    # Match base64 data URLs
    pattern = r'data:[^;]+;base64,[A-Za-z0-9+/=]+'
    
    matches = re.findall(pattern, text)
    bytes_removed = sum(len(m) for m in matches)
    
    cleaned = re.sub(pattern, '<base64_data_removed>', text)
    
    return cleaned, bytes_removed


def compress_message(message: BaseMessage, config: dict) -> BaseMessage:
    """
    Compress a single message based on config.
    
    Args:
        message: LangChain message
        config: Compression config dict
        
    Returns:
        Compressed message (may be same object if no changes)
    """
    content = message.content
    
    if isinstance(content, str):
        # String content
        if config.get("compress_whitespace"):
            content = compress_whitespace(content)
        
        # Remove base64 from non-image contexts
        if config.get("remove_base64"):
            content, _ = remove_base64_from_text(content)
        
        # Truncate tool results
        if isinstance(message, ToolMessage) and config.get("max_tool_result_chars"):
            max_chars = config["max_tool_result_chars"]
            if config.get("summarize_tool_results"):
                content = summarize_tool_result(content, max_chars)
            else:
                content = truncate_text(content, max_chars)
        
        # Return new message with compressed content
        if content != message.content:
            return type(message)(
                content=content,
                **{k: v for k, v in message.__dict__.items() if k != "content"}
            )
    
    elif isinstance(content, list):
        # Multimodal content - compress text parts
        new_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if config.get("compress_whitespace"):
                    text = compress_whitespace(text)
                new_parts.append({"type": "text", "text": text})
            else:
                new_parts.append(part)
        
        if new_parts != content:
            return type(message)(
                content=new_parts,
                **{k: v for k, v in message.__dict__.items() if k != "content"}
            )
    
    return message


def compress_messages(messages: List[BaseMessage], config: dict) -> List[BaseMessage]:
    """Compress all messages in a list."""
    return [compress_message(msg, config) for msg in messages]
