from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID

from src.backend.requirement_gather.requirement_agent.prompt import SYSTEM_PROMPT
from src.backend.config import Config
from src.backend.requirement_gather.requirement_agent.tools.save_requirement_spec import make_save_requirement_spec_tool
from src.backend.requirement_gather.requirement_agent.tools.get_current_requirement_draft import make_get_requirement_draft_tool
from src.backend.requirement_gather.constants import RequirementAgentConstants


class RequirementAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self):
        return ChatOpenAI(
            model=RequirementAgentConstants.MODEL,
            temperature=RequirementAgentConstants.TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )

    def _create_tools(self):
        return [
            make_save_requirement_spec_tool(
                self.user_id,
                self.project_id
            ),
            make_get_requirement_draft_tool(
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
        """Looks for the tool output of save_requirement_specification to find the document_id."""
        for i, message in enumerate(response_messages):
            tool_calls = getattr(message, "tool_calls", None) or []
            for tool_call in tool_calls:
                if tool_call.get("name") == "save_requirement_specification":
                    # The next message should be the ToolMessage with the result
                    if i + 1 < len(response_messages):
                        tool_msg = response_messages[i+1]
                        # Langchain ToolMessage has a content attribute which is the tool output
                        import json
                        try:
                            content = getattr(tool_msg, "content", "")
                            if isinstance(content, str):
                                data = json.loads(content)
                                if data.get("status") == "success":
                                    return data.get("result", {}).get("document_id")
                        except:
                            pass
        return None

    def _extract_doc(self, response_messages: List[Any]) -> str:
        for message in reversed(response_messages):
            tool_calls = getattr(message, "tool_calls", None) or []
            for tool_call in tool_calls:
                if tool_call.get("name") == "save_requirement_specification":
                    return tool_call.get("args", {}).get("markdown_content", "")
        return ""

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
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
