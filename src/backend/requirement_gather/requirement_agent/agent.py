from src.backend.utils.agent_utils import create_agent, get_last_ai_content, extract_tool_args, get_tool_call, is_tool_successful
from langchain_openai import ChatOpenAI
from typing import Any, Dict, List
from uuid import UUID
import json
import logging

from src.backend.requirement_gather.requirement_agent.prompt import SYSTEM_PROMPT
from src.backend.config import settings
from src.backend.requirement_gather.constants import RequirementAgentConstants
from src.backend.requirement_gather.requirement_agent.tools.save_requirement_spec import save_requirement_spec_tool
from src.backend.requirement_gather.requirement_agent.tools.get_current_requirement_draft import get_requirement_draft_tool

logger = logging.getLogger(__name__)


class RequirementAgent:

    def __init__(self, user_id: UUID, project_id: UUID):
        self.user_id = user_id
        self.project_id = project_id
        self.agent = create_agent(
            model=RequirementAgentConstants.MODEL,
            tools=[
                save_requirement_spec_tool(user_id, project_id),
                get_requirement_draft_tool(project_id)
            ],
            system_prompt=SYSTEM_PROMPT
        )


    def run(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        logger.info(f"Running RequirementAgent for project {self.project_id}")
        response = self.agent.invoke({"messages": messages})
        response_messages = response["messages"]

        content = get_last_ai_content(response_messages)
        doc_args = extract_tool_args(response_messages, "save_requirement_specification")
        document = doc_args.get("markdown_content", "")

        return {
            "content": content,
            "document": document,
            "saved": is_tool_successful(response_messages, "save_requirement_specification"),
        }