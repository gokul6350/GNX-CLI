import re
import json
import logging
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

# Configure logging to file
logging.basicConfig(
    filename='app0.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReActAdapter:
    """
    Wraps a ChatModel to support ReAct-style prompting while mimicking native tool calling.
    Required for models like Gemma 3 that don't support native function calling but must be used with
    agent frameworks like DeepAgents/LangGraph that expect it.
    """
    def __init__(self, model: BaseChatModel):
        self.model = model
        self.tools = []
        self.tool_map = {}
        
    def bind_tools(self, tools, **kwargs):
        """Intercept tool binding and store tools for prompt generation."""
        print(f"DEBUG: ReActAdapter.bind_tools called with {len(tools)} tools")
        self.tools = tools
        for t in tools:
            name = getattr(t, "name", str(t))
            self.tool_map[name] = t
        return self
        
    def bind(self, *args, **kwargs):
        print(f"DEBUG: ReActAdapter.bind called with args={args} kwargs={kwargs.keys()}")
        # Check if tools are being bound here
        if "tools" in kwargs or "functions" in kwargs:
             print("DEBUG: Intercepting tools in bind()")
             if "tools" in kwargs:
                 self.bind_tools(kwargs.pop("tools"))
        return self

    def __getattr__(self, name):
        return getattr(self.model, name)

    def invoke(self, input, **kwargs):
        print(f"DEBUG: ReActAdapter.invoke called. Kwargs keys: {list(kwargs.keys())}")
        # 1. Extract messages from input
        messages = input if isinstance(input, list) else input.get("messages", [])
        
        # Log message types
        msg_types = [type(m).__name__ for m in messages]
        print(f"DEBUG: Input message types: {msg_types}")
        
        # 2. Inject ReAct system prompt if we have tools and no system message exists
        if self.tools and not any(isinstance(m, SystemMessage) and "Available Tools:" in m.content for m in messages):
            print("DEBUG: Injecting ReAct system prompt")
            tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
            react_prompt = (
                f"You have access to the following tools:\n{tool_desc}\n\n"
                "To use a tool, you MUST use the following format:\n"
                "Thought: your reasoning here\n"
                "Action: [tool_name]\n"
                "Action Input: [json string of arguments]\n\n"
                "If you do not need to use a tool, output the final answer directly.\n"
                "Example:\n"
                "Thought: I need to list files.\n"
                "Action: ls\n"
                "Action Input: {}\n"
            )
            # Prepend SystemMessage
            messages = [SystemMessage(content=react_prompt)] + messages
        
        # 3. Convert SystemMessage to HumanMessage for Gemma 3, and ToolMessage to HumanMessage
        # Gemma 3 doesn't support 'Developer instruction' (SystemMessage) or ToolMessage
        final_messages = []
        system_content = ""
        
        for m in messages:
            if isinstance(m, SystemMessage):
                system_content += m.content + "\n\n"
            elif isinstance(m, ToolMessage):
                # Convert tool result message to human message so Gemma can process it
                tool_result = f"Tool Result ({m.name}): {m.content}"
                final_messages.append(HumanMessage(content=tool_result))
            else:
                final_messages.append(m)
        
        if system_content:
            # Prepend to first HumanMessage if it exists
            if final_messages and isinstance(final_messages[0], HumanMessage):
                # We need to create a NEW message to avoid mutating original
                original_first = final_messages[0]
                new_first = HumanMessage(content=system_content + str(original_first.content))
                final_messages[0] = new_first
            else:
                # No HumanMessage? Just add as HumanMessage
                final_messages.insert(0, HumanMessage(content=system_content))
        
        # 4. Strip ALL tool and function-calling related kwargs that might trigger API errors
        # DeepAgents/LangGraph might pass various tool-related parameters
        for key in list(kwargs.keys()):
            if any(x in key.lower() for x in ['tool', 'function', 'bind', 'tool_choice']):
                kwargs.pop(key, None)
        
        print(f"DEBUG: Calling model.invoke. Kwargs keys after strip: {list(kwargs.keys())}")
        
        # 5. Call the real model
        try:
            response = self.model.invoke(final_messages, **kwargs)
        except Exception as e:
            print(f"DEBUG: Model invoke failed: {e}")
            raise e
        
        # 6. DO NOT set tool_calls on response - this triggers function calling mode in the API
        # Instead, just return the response as-is with the ReAct content
        # DeepAgents will parse the ReAct format from the content itself
        return response
