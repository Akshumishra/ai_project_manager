from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID
import json

from src.backend.requirement_gather.requirement_agent.prompt import SYSTEM_PROMPT
from src.backend.config import settings
from src.backend.requirement_gather.requirement_agent.tools.save_requirement_spec import save_requirement_spec_tool
from src.backend.requirement_gather.requirement_agent.tools.get_current_requirement_draft import get_requirement_draft_tool
from src.backend.requirement_gather.constants import RequirementAgentConstants


class RequirementAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self):
        model_name = RequirementAgentConstants.MODEL
        kwargs = {
            "model": model_name,
            "api_key": settings.OPENAI_API_KEY
        }
        if not (model_name.startswith("o1") or model_name.startswith("o3")):
            kwargs["temperature"] = RequirementAgentConstants.TEMPERATURE
            
        return ChatOpenAI(**kwargs)

    def _create_tools(self):
        return [
            save_requirement_spec_tool(
                self.user_id,
                self.project_id
            ),
            get_requirement_draft_tool(
                self.project_id
            )
        ]

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT
        )


    def _was_save_tool_called(self, response_messages: List[Any]) -> bool:
        for message in response_messages:
            tool_calls = getattr(message, "tool_calls", None) or []

            for tool_call in tool_calls:
                if tool_call.get("name") == "save_requirement_specification":
                    return True

        return False

    def _extract_document_id(self, response_messages: List[Any]) -> str | None:
        """
        Filters the messages to find the successful output of the save_requirement_specification tool
        and extracts the document_id.
        """
        # Search for messages that have a 'name' matching our tool 
        # (This is usually a ToolMessage containing the tool's result)
        for msg in reversed(response_messages):
            if getattr(msg, "name", None) != "save_requirement_specification":
                continue
            
            content = getattr(msg, "content", "")
            if not isinstance(content, str):
                continue

            try:
                data = json.loads(content)
                if data.get("status") == "success":
                    return data.get("result", {}).get("document_id")
            except (json.JSONDecodeError, AttributeError):
                continue
                
        return None

    def _extract_doc(self, response_messages: List[Any]) -> str:
        for message in reversed(response_messages):
            tool_calls = getattr(message, "tool_calls", None) or []
            for tool_call in tool_calls:
                if tool_call.get("name") == "save_requirement_specification":
                    return tool_call.get("args", {}).get("markdown_content", "")
        return ""

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            response = self.agent.invoke({
                "messages": messages
            })
            response_messages = response["messages"]
            last_message = response_messages[-1]
            
            content = getattr(last_message, "content", "")
            if not isinstance(content, str):
                content = str(content)

            return {
                "content": content,
                "doc": self._extract_doc(response_messages),
                "saved": self._was_save_tool_called(response_messages),
                "document_id": self._extract_document_id(response_messages)
            }
        except Exception as e:
            print(f"Error running agent: {e}")
            return {
                "content": f"I'm sorry, I encountered an error while processing your request: {str(e)}",
                "doc": "",
                "saved": False,
                "document_id": None
            }
