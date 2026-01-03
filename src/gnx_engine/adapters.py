import re
import json
import logging
import time
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from . import engine
from .prompts import build_react_system_prompt
from src.utils.logger_client import history_logger
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

class ReActAdapter:
    """
    Wraps a ChatModel to support ReAct-style prompting with actual tool execution.
    Required for models like Gemma 3 that don't support native function calling.
    This adapter handles the complete ReAct loop: parse output, execute tools, loop until final answer.
    """
    MAX_ITERATIONS = 10  # Prevent infinite loops
    
    def __init__(self, model: BaseChatModel):
        self.model = model
        self.tools = []
        self.tool_map = {}
        
    def bind_tools(self, tools, **kwargs):
        """Intercept tool binding and store tools for prompt generation."""
        logger.debug(f"ReActAdapter.bind_tools called with {len(tools)} tools")
        self.tools = tools
        self.tool_map = {}
        for t in tools:
            name = getattr(t, "name", str(t))
            self.tool_map[name] = t
            logger.debug(f"Registered tool: {name}")
        return self
        
    def bind(self, *args, **kwargs):
        logger.debug(f"ReActAdapter.bind called with args={args} kwargs={kwargs.keys()}")
        if "tools" in kwargs or "functions" in kwargs:
            logger.debug("Intercepting tools in bind()")
            if "tools" in kwargs:
                self.bind_tools(kwargs.pop("tools"))
        return self

    def __getattr__(self, name):
        return getattr(self.model, name)
    
    def _parse_react_output(self, content: str):
        """Parse ReAct output to extract action and action input."""
        # Pattern to match Action: tool_name and Action Input: {...}
        action_pattern = re.compile(
            r"Action:\s*([^\n]+)\s*\nAction Input:\s*(.*?)(?=\n\n|$)", 
            re.DOTALL | re.IGNORECASE
        )
        match = action_pattern.search(content)
        
        if match:
            action_name = match.group(1).strip()
            action_input_str = match.group(2).strip()
            
            # Skip if action is None or empty
            if action_name.lower() in ['none', 'n/a', ''] or not action_name:
                logger.debug(f"Skipping None/empty action")
                return None, None
            
            # Clean up potential markdown or extra chars
            action_input_str = action_input_str.strip('`').strip()
            if action_input_str.startswith('json'):
                action_input_str = action_input_str[4:].strip()
            
            logger.debug(f"Parsed action: {action_name}, input: {action_input_str}")
            
            try:
                args = json.loads(action_input_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues or treat as single string arg
                logger.debug(f"JSON parse failed, attempting recovery")
                args = {"input": action_input_str}
            
            # Fix paths: remove leading slash for relative paths
            if 'path' in args and isinstance(args['path'], str):
                path = args['path']
                # Remove leading / for relative paths (common mistake)
                if path.startswith('/') and not path.startswith('//'):
                    args['path'] = path.lstrip('/')
                    logger.debug(f"Fixed path: {path} -> {args['path']}")
                
            return action_name, args
        
        return None, None
    
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
            logger.debug(f"Tool result: {result[:200] if len(str(result)) > 200 else result}")
            return str(result)
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {e}"
            logger.error(error_msg)
            return error_msg
    
    def _build_messages_for_gemma(self, messages: list) -> list:
        """Convert messages to Gemma-compatible format (no SystemMessage)."""
        final_messages = []
        system_content = ""
        
        for m in messages:
            if isinstance(m, SystemMessage):
                system_content += m.content + "\n\n"
            elif isinstance(m, ToolMessage):
                # Convert tool result to human message
                tool_result = f"Observation: {m.content}"
                final_messages.append(HumanMessage(content=tool_result))
            else:
                final_messages.append(m)
        
        if system_content:
            if final_messages and isinstance(final_messages[0], HumanMessage):
                original_first = final_messages[0]
                new_first = HumanMessage(content=system_content + str(original_first.content))
                final_messages[0] = new_first
            else:
                final_messages.insert(0, HumanMessage(content=system_content))
        
        return final_messages

    def invoke(self, input, **kwargs):
        logger.debug(f"ReActAdapter.invoke called. Kwargs keys: {list(kwargs.keys())}")
        
        # Extract messages from input
        messages = input if isinstance(input, list) else input.get("messages", [])
        
        msg_types = [type(m).__name__ for m in messages]
        logger.debug(f"Input message types: {msg_types}")
        
        # Build the ReAct system prompt
        if self.tools:
            react_prompt = build_react_system_prompt(self.tools, self.tool_map)
            messages = [SystemMessage(content=react_prompt)] + list(messages)
        
        # Strip tool-related kwargs
        for key in list(kwargs.keys()):
            if any(x in key.lower() for x in ['tool', 'function', 'bind', 'tool_choice']):
                kwargs.pop(key, None)
        
        # ReAct loop
        iteration = 0
        conversation = list(messages)
        max_retries = 3
        retry_count = 0
        
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.debug(f"ReAct iteration {iteration}")
            
            # Convert to Gemma-compatible format
            gemma_messages = self._build_messages_for_gemma(conversation)
            
            # Call the model with spinner animation and retry logic
            try:
                with console.status("[bold cyan]  thinking...[/bold cyan]", spinner="dots"):
                    response = self.model.invoke(gemma_messages, **kwargs)
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
            
            content = response.content
            logger.debug(f"Model response: {content[:300]}...")
            
            # Log AI Thought/Action (Intermediate)
            history_logger.log("ai", content, is_context=False)

            # Parse for tool call
            action_name, action_args = self._parse_react_output(content)
            
            if action_name:
                # Print tool call LIVE
                args_str = json.dumps(action_args) if action_args else "{}"
                print_tool_call(action_name, args_str)
                
                # Execute the tool
                tool_result = self._execute_tool(action_name, action_args)
                
                # Log Tool Result
                history_logger.log("tool_result", tool_result, is_context=False, metadata={"tool": action_name})
                
                # Check for image paths in tool result (auto-log images)
                import os
                if isinstance(tool_result, str) and any(ext in tool_result.lower() for ext in ['.png', '.jpg', '.jpeg']):
                    possible_path = tool_result.strip()
                    # Handle potential "Screenshot saved to: path" format
                    if ": " in possible_path:
                        possible_path = possible_path.split(": ")[-1].strip()
                    
                    if os.path.exists(possible_path) and os.path.isfile(possible_path):
                        history_logger.log_image(possible_path)

                # Print tool result LIVE
                print_tool_result(tool_result)
                
                # Add AI response and tool result to conversation
                conversation.append(AIMessage(content=content))
                conversation.append(HumanMessage(content=f"Observation: {tool_result}"))
                
                logger.debug(f"Tool executed, continuing loop")
            else:
                # No tool call - this is the final answer
                logger.debug("No tool call detected, returning final response")
                # Clean up the response - remove any ReAct artifacts
                response.content = self._clean_final_response(content)
                return response
        
        # Max iterations reached
        logger.warning(f"Max iterations ({self.MAX_ITERATIONS}) reached")
        response.content = self._clean_final_response(response.content)
        return response
    
    def _clean_final_response(self, content: str) -> str:
        """Remove ReAct formatting artifacts from final response."""
        import re
        
        # Remove "Thought: ..." lines
        content = re.sub(r'^Thought:.*?\n?', '', content, flags=re.MULTILINE)
        
        # Remove "Action: None" or "Action: none" lines (model bad habit)
        content = re.sub(r'^Action:\s*[Nn]one\s*\n?', '', content, flags=re.MULTILINE)
        
        # Remove any other "Action: ..." and "Action Input: ..." if present
        content = re.sub(r'^Action:.*?\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^Action Input:.*?\n?', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # Remove "Observation: ..." lines that might leak through
        content = re.sub(r'^Observation:.*?\n?', '', content, flags=re.MULTILINE)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
