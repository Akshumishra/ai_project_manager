import json
import logging

from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.backend.config import settings
from src.backend.meeting_bot.constants import (
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TEMPERATURE,
    AGENT_MAX_ITERATIONS,
)
from .prompts import SYSTEM_PROMPT
from .tools import (
    get_pending_tasks,
    create_task,
    update_task,
    match_participant_by_domain,
    log_risk,
    flag_for_review,
)

logger = logging.getLogger(__name__)


def run_task_mapping_agent(context: dict) -> str:
    """
    Executes decision making loop with tool calling for task mapper using a manual execution loop.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    llm = ChatOpenAI(
        model=DEFAULT_AI_MODEL, temperature=DEFAULT_AI_TEMPERATURE, api_key=api_key
    )
    tools = [
        get_pending_tasks,
        create_task,
        update_task,
        match_participant_by_domain,
        log_risk,
        flag_for_review,
    ]
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"Here is the context data to reconcile:\n\n{json.dumps(context, indent=2)}"
        ),
    ]

    tool_map = {t.name: t for t in tools}

    for _ in range(AGENT_MAX_ITERATIONS):
        try:
            response = llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return (
                    response.content if hasattr(response, "content") else str(response)
                )

            print(
                f"\n--- Model triggered tool calls: {[t['name'] for t in response.tool_calls]} ---"
            )
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                if tool_name not in tool_map:
                    print(f"Unknown tool: {tool_name}")
                    continue

                tool_func = tool_map[tool_name]
                try:
                    tool_output = tool_func.invoke(tool_args)
                    print(f"Tool {tool_name} output: {tool_output}")

                    messages.append(
                        ToolMessage(content=str(tool_output), tool_call_id=tool_id)
                    )
                except Exception as e:
                    print(f"Tool {tool_name} failed: {e}")
                    messages.append(
                        ToolMessage(
                            content=f"Error running tool: {e}", tool_call_id=tool_id
                        )
                    )

        except Exception as e:
            logger.exception("Agent execution cycle failed")
            return f"Error running AI agent: {str(e)}"

    return "Agent loop timed out without reaching final structured response."
