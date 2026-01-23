"""
Context pruning logic for token optimization.
"""

from typing import List, Set, Tuple

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage


def identify_essential_messages(messages: List[BaseMessage], keep_last: int = 4) -> Set[int]:
    """
    Identify indices of messages that should not be pruned.
    
    Essential messages:
    - System messages
    - Last N messages
    - Messages with tool calls and their results
    
    Returns:
        Set of indices to preserve
    """
    essential = set()
    n = len(messages)
    
    for i, msg in enumerate(messages):
        # Always keep system messages
        if isinstance(msg, SystemMessage):
            essential.add(i)
        
        # Keep last N messages
        if i >= n - keep_last:
            essential.add(i)
    
    # Keep paired tool calls and results
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, 'tool_calls', None)
            if tool_calls:
                essential.add(i)
                # Find corresponding tool messages
                for j in range(i + 1, min(i + len(tool_calls) + 1, n)):
                    if isinstance(messages[j], ToolMessage):
                        essential.add(j)
    
    return essential


def prune_oldest_messages(
    messages: List[BaseMessage],
    target_count: int,
    preserve_essential: bool = True,
) -> Tuple[List[BaseMessage], int]:
    """
    Remove oldest non-essential messages to reach target count.
    
    Args:
        messages: List of messages
        target_count: Target number of messages
        preserve_essential: Whether to preserve essential messages
        
    Returns:
        (pruned_messages, count_removed)
    """
    if len(messages) <= target_count:
        return messages, 0
    
    if preserve_essential:
        essential = identify_essential_messages(messages)
    else:
        essential = set()
    
    # Find messages we can prune (oldest first that aren't essential)
    prunable = [i for i in range(len(messages)) if i not in essential]
    
    # Calculate how many to remove
    to_remove = len(messages) - target_count
    remove_indices = set(prunable[:to_remove])
    
    # Build result
    result = [msg for i, msg in enumerate(messages) if i not in remove_indices]
    
    return result, len(remove_indices)


def prune_images(
    messages: List[BaseMessage],
    max_images: int = 3,
) -> Tuple[List[BaseMessage], int]:
    """
    Remove old image content, keeping only the most recent N images.
    
    Args:
        messages: List of messages
        max_images: Maximum images to keep
        
    Returns:
        (pruned_messages, images_removed)
    """
    # Find all message indices with images
    image_indices = []
    
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage) and isinstance(msg.content, list):
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    image_indices.append(i)
                    break
    
    if len(image_indices) <= max_images:
        return messages, 0
    
    # Remove images from oldest messages
    indices_to_strip = set(image_indices[:-max_images])
    
    result = []
    images_removed = 0
    
    for i, msg in enumerate(messages):
        if i in indices_to_strip:
            # Strip images from this message
            new_content = []
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    new_content.append({
                        "type": "text",
                        "text": "<image removed for token optimization>"
                    })
                    images_removed += 1
                else:
                    new_content.append(part)
            result.append(HumanMessage(content=new_content))
        else:
            result.append(msg)
    
    return result, images_removed


def find_duplicate_content(messages: List[BaseMessage], threshold: float = 0.9) -> List[int]:
    """
    Find indices of messages with near-duplicate content.
    Uses simple length-based heuristic (no embeddings needed).
    
    Returns:
        List of indices that are duplicates of earlier messages
    """
    duplicates = []
    seen_hashes = {}
    
    for i, msg in enumerate(messages):
        # Skip non-text messages
        if not isinstance(msg.content, str):
            continue
        
        # Simple hash based on content length and first/last chars
        content = msg.content.strip()
        if len(content) < 20:
            continue
        
        key = (len(content), content[:50], content[-50:])
        
        if key in seen_hashes:
            duplicates.append(i)
        else:
            seen_hashes[key] = i
    
    return duplicates


def prune_duplicates(messages: List[BaseMessage]) -> Tuple[List[BaseMessage], int]:
    """
    Remove duplicate messages.
    
    Returns:
        (pruned_messages, count_removed)
    """
    duplicate_indices = set(find_duplicate_content(messages))
    
    result = [msg for i, msg in enumerate(messages) if i not in duplicate_indices]
    
    return result, len(duplicate_indices)
