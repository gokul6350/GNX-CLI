import json
import logging
import time
import os
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from .prompts import build_system_prompt
from src.utils.logger_client import history_logger
from src.utils.debug_logger import debug

# Configure logging to file
logging.basicConfig(
    filename='app0.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Import display functions for live output
from src.ui.display import print_tool_call, print_tool_result, console


class NativeToolAdapter:
    """
    Adapter for LLMs with native tool calling support (like Llama 4 Scout).
    Uses LangChain's bind_tools() and handles tool_calls from AIMessage.
    Supports multimodal inputs (images) for vision-capable models.
    """
    MAX_ITERATIONS = 15  # Prevent infinite loops
    MAX_IMAGES_IN_CONTEXT = 3  # Keep last 3 screenshots in context
    
    def __init__(self, model: BaseChatModel):
        self.model = model
        self.tools = []
        self.tool_map = {}
        self.model_with_tools = None
        
    def bind_tools(self, tools, **kwargs):
        """Bind tools to the model using native tool calling."""
        logger.debug(f"NativeToolAdapter.bind_tools called with {len(tools)} tools")
        self.tools = tools
        self.tool_map = {}
        for t in tools:
            name = getattr(t, "name", str(t))
            self.tool_map[name] = t
            logger.debug(f"Registered tool: {name}")
        
        # Use LangChain's native bind_tools
        self.model_with_tools = self.model.bind_tools(tools, tool_choice="auto")
        return self
        
    def bind(self, *args, **kwargs):
        logger.debug(f"NativeToolAdapter.bind called with args={args} kwargs={kwargs.keys()}")
        if "tools" in kwargs or "functions" in kwargs:
            logger.debug("Intercepting tools in bind()")
            if "tools" in kwargs:
                self.bind_tools(kwargs.pop("tools"))
        return self

    def __getattr__(self, name):
        return getattr(self.model, name)
    
    def _execute_tool(self, tool_name: str, args: dict) -> str:
        """Execute a tool and return its result."""
        logger.debug(f"Executing tool: {tool_name} with args: {args}")
        
        if tool_name not in self.tool_map:
            error_msg = f"Unknown tool: {tool_name}. Available tools: {list(self.tool_map.keys())}"
            logger.error(error_msg)
            return error_msg
        
        tool = self.tool_map[tool_name]
        
        try:
            # LangChain tools can be invoked with .invoke() or called directly
            if hasattr(tool, 'invoke'):
                result = tool.invoke(args)
            else:
                result = tool(**args)
            logger.debug(f"Tool result: {str(result)[:200]}...")
            return str(result)
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {e}"
            logger.error(error_msg)
            return error_msg

    def _parse_screenshot_payload(self, tool_result: str):
        """Extract screenshot payload if tool_result is JSON with data_url."""
        try:
            obj = json.loads(tool_result)
            if isinstance(obj, dict) and obj.get("type") == "screenshot" and obj.get("data_url"):
                return obj
        except Exception:
            return None
        return None

    def _clean_tool_result_for_context(self, tool_result: str, tool_name: str) -> str:
        """
        Clean tool result by removing large base64 data before adding to conversation.
        This prevents inflating token count with image data that's already in an image message.
        """
        if tool_name in ["computer_screenshot", "mobile_screenshot"]:
            try:
                obj = json.loads(tool_result)
                if isinstance(obj, dict) and obj.get("data_url"):
                    # Keep metadata but remove the massive base64 string
                    cleaned = {
                        "type": obj.get("type"),
                        "path": obj.get("path"),
                        "width": obj.get("width"),
                        "height": obj.get("height"),
                        "note": obj.get("note", ""),
                        "data_url": "<image_data_moved_to_multimodal_message>"
                    }
                    debug.tool(f"Cleaned screenshot result", {
                        "original_len": len(tool_result),
                        "cleaned_len": len(json.dumps(cleaned)),
                        "saved": f"{(len(tool_result) - len(json.dumps(cleaned))) / 1024:.1f} KB"
                    })
                    return json.dumps(cleaned)
            except Exception as e:
                debug.warn(f"Failed to clean tool result: {e}")
        return tool_result

    def _build_image_message_content(self, text: str, data_url: str = None) -> list:
        """Build multimodal content list with text and optional image."""
        content = [{"type": "text", "text": text}]
        if data_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        return content

    def _strip_images_from_message(self, message: HumanMessage) -> HumanMessage:
        """Replace image content with placeholder text for token optimization."""
        if not isinstance(message.content, list):
            return message
        
        new_content = []
        for part in message.content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                new_content.append({
                    "type": "text",
                    "text": "<system>THE IMAGE IS NOT AVAILABLE DUE TO TOKEN OPTIMIZATION</system>"
                })
            else:
                new_content.append(part)
        
        return HumanMessage(content=new_content)

    def _optimize_images_in_conversation(self, messages: list) -> list:
        """Keep only the latest N images in conversation, replace older ones with placeholder."""
        # Find all messages with images (track indices)
        image_indices = []
        for i, msg in enumerate(messages):
            if isinstance(msg, HumanMessage) and isinstance(msg.content, list):
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        image_indices.append(i)
                        break
        
        # If we have more images than allowed, strip older ones
        if len(image_indices) > self.MAX_IMAGES_IN_CONTEXT:
            indices_to_strip = image_indices[:-self.MAX_IMAGES_IN_CONTEXT]
            optimized = []
            for i, msg in enumerate(messages):
                if i in indices_to_strip:
                    optimized.append(self._strip_images_from_message(msg))
                else:
                    optimized.append(msg)
            return optimized
        
        return messages

    def invoke(self, input, **kwargs):
        """Execute the tool calling loop with native tool support."""
        logger.debug(f"NativeToolAdapter.invoke called. Kwargs keys: {list(kwargs.keys())}")
        
        if self.model_with_tools is None:
            raise ValueError("Tools not bound. Call bind_tools() first.")
        
        # Extract messages from input
        messages = input if isinstance(input, list) else input.get("messages", [])
        
        msg_types = [type(m).__name__ for m in messages]
        logger.debug(f"Input message types: {msg_types}")
        
        # Build the system prompt
        if self.tools:
            system_prompt = build_system_prompt(self.tools, self.tool_map)
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        
        # Tool calling loop
        iteration = 0
        conversation = list(messages)
        max_retries = 3
        retry_count = 0
        
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.debug(f"Tool calling iteration {iteration}")
            
            # Optimize images in conversation to save tokens
            optimized_conversation = self._optimize_images_in_conversation(conversation)
            
            # Count tokens before sending
            from src.utils.token_counter import count_messages_tokens
            token_count = count_messages_tokens(optimized_conversation)
            console.print(f"[dim]📊 Sending {token_count:,} tokens to model...[/dim]")
            
            # Call the model with native tool calling
            try:
                with console.status("[bold cyan]  thinking...[/bold cyan]", spinner="dots"):
                    response = self.model_with_tools.invoke(optimized_conversation, **kwargs)
                retry_count = 0  # Reset retry count on success
            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limit error
                if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or 
                    "quota" in error_str.lower() or "rate" in error_str.lower()):
                    
                    if retry_count < max_retries:
                        retry_count += 1
                        wait_time = 2 ** retry_count  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"Rate limit hit. Retry {retry_count}/{max_retries}, waiting {wait_time}s")
                        console.print(f"[yellow]⚠️  Rate limit hit. Waiting {wait_time}s before retry... ({retry_count}/{max_retries})[/yellow]")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for rate limit: {e}")
                        raise e
                else:
                    logger.error(f"Model invoke failed: {e}")
                    raise e
            
            content = response.content or ""
            logger.debug(f"Model response content: {content[:300]}...")
            
            # Log AI response (including any text before tool calls)
            if content:
                history_logger.log("ai", content, is_context=False)
            
            # Check for tool calls in the response
            tool_calls = getattr(response, 'tool_calls', None) or []
            
            if not tool_calls:
                # No tool calls - this is the final answer
                logger.debug("No tool calls detected, returning final response")
                conversation.append(response)
                return conversation
            
            # Process each tool call
            conversation.append(response)  # Add AI message with tool calls
            
            for tool_call in tool_calls:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})
                tool_id = tool_call.get('id', f'call_{iteration}')
                
                # Print tool call LIVE
                args_str = json.dumps(tool_args) if tool_args else "{}"
                print_tool_call(tool_name, args_str)
                
                # Execute the tool
                tool_result = self._execute_tool(tool_name, tool_args)
                
                # Log Tool Result (full version with base64 for history)
                history_logger.log("tool_result", tool_result, is_context=False, metadata={"tool": tool_name})
                
                # Check for screenshot payload
                screenshot_payload = None
                if tool_name in ["computer_screenshot", "mobile_screenshot"]:
                    screenshot_payload = self._parse_screenshot_payload(tool_result)
                
                # Log images if found
                if screenshot_payload and screenshot_payload.get("path") and os.path.exists(screenshot_payload.get("path")):
                    history_logger.log_image(screenshot_payload.get("path"))
                elif isinstance(tool_result, str) and any(ext in tool_result.lower() for ext in ['.png', '.jpg', '.jpeg']):
                    possible_path = tool_result.strip()
                    if ": " in possible_path:
                        possible_path = possible_path.split(": ")[-1].strip()
                    if os.path.exists(possible_path) and os.path.isfile(possible_path):
                        history_logger.log_image(possible_path)
                
                # Clean tool result for display (removes large base64 data from console output)
                cleaned_result = self._clean_tool_result_for_context(tool_result, tool_name)
                
                # Print cleaned tool result LIVE (without huge base64 data in console)
                print_tool_result(cleaned_result)
                tool_message = ToolMessage(
                    content=cleaned_result,
                    tool_call_id=tool_id,
                    name=tool_name
                )
                conversation.append(tool_message)
                debug.tool(f"Added ToolMessage for {tool_name}", {
                    "content_len": len(cleaned_result)
                })
                
                # If screenshot with image, add as multimodal message for model to see
                if screenshot_payload and screenshot_payload.get("data_url"):
                    width = screenshot_payload.get("width", "?")
                    height = screenshot_payload.get("height", "?")
                    path = screenshot_payload.get("path", "screenshot")
                    note = screenshot_payload.get("note", "")
                    
                    obs_text = f"Screenshot captured ({width}x{height}) from {path}"
                    if note:
                        obs_text += f" - {note}"
                    
                    # Add multimodal observation with image
                    image_content = self._build_image_message_content(
                        obs_text,
                        screenshot_payload.get("data_url")
                    )
                    conversation.append(HumanMessage(content=image_content))
                    
                    debug.image(f"Added screenshot to conversation", {
                        "dimensions": f"{width}x{height}",
                        "path": path,
                        "data_url_len": f"{len(screenshot_payload.get('data_url', '')) / 1024:.1f} KB"
                    })
                    logger.debug(f"Added screenshot image to conversation")
            
            logger.debug(f"Processed {len(tool_calls)} tool calls, continuing loop")
        
        # Max iterations reached
        logger.warning(f"Max iterations ({self.MAX_ITERATIONS}) reached")
        return conversation


# Alias for backwards compatibility
ReActAdapter = NativeToolAdapter
