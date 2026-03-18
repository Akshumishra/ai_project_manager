from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID
import json
import re

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
        return ChatOpenAI(
            model=RequirementAgentConstants.MODEL,
            api_key=settings.OPENAI_API_KEY
        )

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
        Filters the messages to find the output of the save_requirement_specification tool.
        """
        for msg in reversed(response_messages):
            if getattr(msg, "name", None) != "save_requirement_specification":
                continue
            
            content = getattr(msg, "content", "")
            if not content:
                continue

            # If it's a dict/json string, parse it
            if isinstance(content, str):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        return data.get("document_id")
                except:
                    pass
            elif isinstance(content, dict):
                return content.get("document_id")
                
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
            
            # Extract conversational content: look for the last AIMessage that has text content
            content = ""
            for msg in reversed(response_messages):
                # We want an AIMessage with content that is NOT just a tool call response
                if hasattr(msg, "content") and msg.content and getattr(msg, "type", "") != "tool":
                    content = msg.content
                    break

            # Fallback to last message if no text found
            if not content and response_messages:
                content = response_messages[-1].content
                if not isinstance(content, str):
                    content = str(content)

            document = self._extract_doc(response_messages)
            
            # Stage 2 Fallback: Transition marker (regex)
            if not document:
                # Matches "— Requirement Specification" or "--- Requirement Specification"
                marker_pattern = r"^[—-]{1,5}\s*Requirement Specification\s*$(.*)"
                marker_match = re.search(marker_pattern, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                if marker_match:
                    document = marker_match.group(1).strip()
            
            # Stage 3 Fallback: Default to heading detection if substantial markdown exists
            if not document:
                # If content contains a level 1 heading, extract from there to the end
                if "# " in content:
                    parts = content.split("# ", 1)
                    if len(parts) > 1:
                        # Only fallback if the suspected document is significant (e.g., > 100 chars)
                        potential_doc = "# " + parts[1].strip()
                        if len(potential_doc) > 100:
                            document = potential_doc

            return {
                "content": content,
                "document": document,
                "doc": document, # For backward compatibility
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
