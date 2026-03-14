from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID

from src.backend.technical_doc.tech_doc_agent.prompt import SYSTEM_PROMPT
from src.backend.config import Config
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.technical_doc.tech_doc_agent.tools.save_tech_doc import make_save_tech_doc_tool
from src.backend.technical_doc.tech_doc_agent.tools.update_tech_doc import make_update_tech_doc_tool

class TechDocAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_llm(self):
        return ChatOpenAI(
            model=TechDocAgentConstants.MODEL,
            temperature=TechDocAgentConstants.TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )

    def _create_tools(self):
        return [
            *make_update_tech_doc_tool(),
            make_save_tech_doc_tool(
                self.user_id,
                self.project_id
            )
        ]

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT
        )

    def _extract_document(self, response_messages: List[Any]) -> str:
        for message in reversed(response_messages):
            tool_calls = getattr(message, "tool_calls", None) or []
            for tool_call in tool_calls:
                if tool_call.get("name") in ["update_technical_document_draft", "save_technical_document"]:
                    return tool_call.get("args", {}).get("document_markdown", "")
        return ""

    def _extract_section_update(self, response_messages: List[Any]) -> Dict[str, str]:
        for message in reversed(response_messages):
            tool_calls = getattr(message, "tool_calls", None) or []
            for tool_call in tool_calls:
                if tool_call.get("name") == "update_technical_document_section":
                    args = tool_call.get("args", {})
                    return {
                        "section_heading": args.get("section_heading", ""),
                        "section_markdown": args.get("section_markdown", ""),
                    }
        return {
            "section_heading": "",
            "section_markdown": "",
        }

    def _was_save_tool_called(self, response_messages: List[Any]) -> bool:
        for message in response_messages:
            tool_calls = getattr(message, "tool_calls", None) or []

            for tool_call in tool_calls:
                if tool_call.get("name") == "save_technical_document":
                    return True

        return False

    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        response = self.agent.invoke({
            "messages": messages
        })
        response_messages = response["messages"]
        section_update = self._extract_section_update(response_messages)

        return {
            "content": response_messages[-1].content,
            "document": self._extract_document(response_messages),
            "section_heading": section_update["section_heading"],
            "section_markdown": section_update["section_markdown"],
            "saved": self._was_save_tool_called(response_messages),
        }
