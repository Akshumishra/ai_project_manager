from typing import Any, Callable, List, Dict, Sequence, Union
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent as langchain_create_agent
from langchain_core.tools import BaseTool
from src.backend.config import settings
from src.backend.constants import DefaultConstants

def create_llm(model_name: str, temperature: float = 0.0):
    """
    Creates a ChatOpenAI instance with the appropriate settings for the given model.
    """
    config = DefaultConstants.MODEL_CONFIG.get(model_name, {})
    
    kwargs = {
        "model": model_name,
        "api_key": settings.OPENAI_API_KEY
    }
    
    if config.get("supports_temperature", True):
        kwargs["temperature"] = temperature
        
    return ChatOpenAI(**kwargs)

def create_agent(
    model: str,
    tools: Sequence[Union[BaseTool, Callable[..., Any], dict[str, Any]]] = None,
    system_prompt: str = None,
    temperature: float = 0.0,
):
    """
    Unified agent creator for the AI Project Manager.
    Wraps the underlying LangChain agent factory with project-specific defaults.
    """
    llm = create_llm(model, temperature)
    
    return langchain_create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt
    )

def get_last_ai_content(messages: List[Any]) -> str:
    """
    Safe helper to extract the last conversational response from an AI,
    skipping intermediate tool messages.
    """
    for msg in reversed(messages):
        if getattr(msg, "type", "") != "tool" and getattr(msg, "content", None):
            return msg.content
    return ""

def get_tool_call(messages: List[Any], tool_names: Union[str, List[str]]):
    """
    Finds the last tool call in a message history by name.
    """
    if isinstance(tool_names, str):
        tool_names = [tool_names]
        
    for msg in reversed(messages):
        call_list = getattr(msg, "tool_calls", []) or []
        for call in call_list:
            if call.get("name") in tool_names:
                return call
    return None

def extract_tool_args(messages: List[Any], tool_names: Union[str, List[str]]) -> dict:
    """
    Extracts the arguments from the last tool call of a given name.
    """
    call = get_tool_call(messages, tool_names)
    return call.get("args", {}) if call else {}

def is_tool_successful(messages: List[Any], tool_name: str, success_marker: str = "Successfully") -> bool:
    """
    Checks if a specific tool was called and returned a success message.
    """
    for msg in messages:
        if getattr(msg, "type", "") == "tool" and getattr(msg, "name", None) == tool_name:
            if success_marker in str(getattr(msg, "content", "")):
                return True
    return False
