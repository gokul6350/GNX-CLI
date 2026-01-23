"""
Hot Tier - Active context buffer using LangChain's ConversationSummaryBufferMemory.
"""

import logging
from typing import List, Optional, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class HotTier:
    """
    Hot Tier Memory Manager.
    
    Uses LangChain's ConversationSummaryBufferMemory to manage the active
    context window. When the buffer exceeds the token limit, oldest messages
    are automatically summarized to save space.
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        max_token_limit: int = 12000,
    ):
        """
        Initialize Hot Tier.
        
        Args:
            llm: LangChain model for summarization (optional)
            max_token_limit: Max tokens before summarization kicks in
        """
        self.max_token_limit = max_token_limit
        self.llm = llm
        self._memory = None
        self._last_summary = ""
        
        # Initialize LangChain memory if LLM provided
        if llm:
            self._init_langchain_memory()
        else:
            # Fallback: simple buffer without summarization
            self._buffer: List[dict] = []
    
    def _init_langchain_memory(self):
        """Initialize LangChain ConversationSummaryBufferMemory."""
        try:
            from langchain.memory import ConversationSummaryBufferMemory
            
            self._memory = ConversationSummaryBufferMemory(
                llm=self.llm,
                max_token_limit=self.max_token_limit,
                return_messages=True,
            )
            logger.info(f"Hot Tier initialized with LangChain memory (limit: {self.max_token_limit})")
        except ImportError:
            logger.warning("LangChain memory not available, using simple buffer")
            self._buffer = []
    
    def add_turn(self, user_input: str, ai_output: str):
        """
        Add a conversation turn to the hot tier.
        
        Args:
            user_input: User's message
            ai_output: AI's response
        """
        if self._memory:
            self._memory.save_context(
                {"input": user_input},
                {"output": ai_output}
            )
        else:
            self._buffer.append({
                "user": user_input,
                "ai": ai_output,
            })
            # Simple pruning: keep last 20 turns
            if len(self._buffer) > 20:
                self._buffer = self._buffer[-20:]
    
    def get_context(self) -> List[Any]:
        """
        Get the current hot context (recent messages).
        
        Returns:
            List of messages or conversation turns
        """
        if self._memory:
            data = self._memory.load_memory_variables({})
            return data.get("history", [])
        else:
            return self._buffer
    
    def get_summary(self) -> str:
        """
        Get the current summary of older conversations.
        LangChain auto-generates this when buffer overflows.
        
        Returns:
            Summary string (empty if no summarization happened)
        """
        if self._memory:
            return self._memory.moving_summary_buffer or ""
        return ""
    
    def has_new_summary(self) -> bool:
        """
        Check if LangChain has generated a new summary.
        
        Returns:
            True if summary changed since last check
        """
        current = self.get_summary()
        if current and current != self._last_summary:
            return True
        return False
    
    def consume_summary(self) -> Optional[str]:
        """
        Get and consume the new summary (marks it as processed).
        
        Returns:
            Summary string if new, None otherwise
        """
        current = self.get_summary()
        if current and current != self._last_summary:
            self._last_summary = current
            return current
        return None
    
    def clear(self):
        """Clear the hot tier buffer."""
        if self._memory:
            self._memory.clear()
        else:
            self._buffer.clear()
        self._last_summary = ""
    
    def size(self) -> int:
        """Return approximate size of hot tier."""
        if self._memory:
            return len(self.get_context())
        return len(self._buffer)
