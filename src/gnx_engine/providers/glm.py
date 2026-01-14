import os
import json
from typing import Any, List, Optional, Sequence, Union
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from zhipuai import ZhipuAI

load_dotenv(override=True)

GLM_CONFIG = {
    "default_model": "GLM-4.5-Flash",
    "env_key": "ZHIPUAI_API_KEY",
    "models": [
        "GLM-4.5-Flash",
        "GLM-4.5-Air",
        "GLM-4.5-AirX",
        "GLM-4-Plus",
        "GLM-4-Air",
    ],
}


def _convert_tool_to_openai_format(tool: BaseTool) -> dict:
    """Convert a LangChain tool to OpenAI function format for ZhipuAI."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.args_schema.schema() if tool.args_schema else {"type": "object", "properties": {}}
        }
    }


class ChatGLMWithTools(BaseChatModel):
    """ChatGLM with tools bound - wrapper for tool calling."""
    
    base_model: Any = None
    tools: List[dict] = []
    tool_choice: str = "auto"
    
    def __init__(self, base_model: Any, tools: List[dict], tool_choice: str = "auto", **kwargs):
        super().__init__(**kwargs)
        self.base_model = base_model
        self.tools = tools
        self.tool_choice = tool_choice
    
    @property
    def _llm_type(self) -> str:
        return "zhipuai-glm-with-tools"
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> ChatResult:
        """Generate with tools."""
        zhipu_messages = self.base_model._convert_messages(messages)
        
        response = self.base_model.client.chat.completions.create(
            model=self.base_model.model_name,
            messages=zhipu_messages,
            tools=self.tools if self.tools else None,
            tool_choice=self.tool_choice if self.tools else None,
            temperature=self.base_model.temperature,
        )
        
        choice = response.choices[0]
        message = choice.message
        
        # Check for tool calls
        tool_calls = []
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments) if tc.function.arguments else {}
                })
        
        content = message.content or ""
        ai_message = AIMessage(content=content, tool_calls=tool_calls)
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])


class ChatGLM(BaseChatModel):
    """Custom GLM chat model using zhipuai SDK directly."""
    
    model_name: str = "GLM-4.5-Flash"
    temperature: float = 0.6
    client: Any = None
    
    def __init__(self, model: str = "GLM-4.5-Flash", temperature: float = 0.6, **kwargs):
        super().__init__(**kwargs)
        self.model_name = model
        self.temperature = temperature
        api_key = os.getenv("ZHIPUAI_API_KEY")
        if not api_key:
            raise ValueError("ZHIPUAI_API_KEY not found in environment")
        self.client = ZhipuAI(api_key=api_key)
    
    @property
    def _llm_type(self) -> str:
        return "zhipuai-glm"
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to ZhipuAI format."""
        result = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                # Handle multimodal messages
                if isinstance(msg.content, list):
                    content_parts = []
                    for part in msg.content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                content_parts.append({"type": "text", "text": part.get("text", "")})
                            elif part.get("type") == "image_url":
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": part.get("image_url", {})
                                })
                        else:
                            content_parts.append({"type": "text", "text": str(part)})
                    result.append({"role": "user", "content": content_parts})
                else:
                    result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                msg_dict = {"role": "assistant", "content": msg.content}
                # Include tool calls if present
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("args", {}))
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                result.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                result.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id
                })
            else:
                result.append({"role": "user", "content": str(msg.content)})
        return result
    
    def bind_tools(
        self,
        tools: Sequence[Union[dict, BaseTool]],
        tool_choice: str = "auto",
        **kwargs
    ) -> "ChatGLMWithTools":
        """Bind tools to the model."""
        formatted_tools = []
        for tool in tools:
            if isinstance(tool, dict):
                formatted_tools.append(tool)
            elif isinstance(tool, BaseTool):
                formatted_tools.append(_convert_tool_to_openai_format(tool))
            else:
                # Try to get schema from tool
                formatted_tools.append(_convert_tool_to_openai_format(tool))
        
        return ChatGLMWithTools(
            base_model=self,
            tools=formatted_tools,
            tool_choice=tool_choice
        )
    
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> ChatResult:
        """Generate a response from the model."""
        zhipu_messages = self._convert_messages(messages)
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=zhipu_messages,
            temperature=self.temperature,
        )
        
        content = response.choices[0].message.content
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[generation])


def create_glm_llm(model_name: str, temperature: float = 0.6):
    """Instantiate the GLM series (text-only) model via ZhipuAI SDK."""
    return ChatGLM(model=model_name, temperature=temperature)
