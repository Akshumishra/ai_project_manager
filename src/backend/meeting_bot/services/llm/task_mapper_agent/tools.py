import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from langchain_core.tools import tool
from sqlalchemy import text

from src.backend.meeting_bot.constants import (
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_TODO,
    TASK_PRIORITY_MEDIUM,
    TASK_CATEGORY_BACKEND,
    DOMAIN_MAPPING,
)
from src.backend.meeting_bot.services.meeting.session import get_db_session

logger = logging.getLogger(__name__)


@tool
def get_pending_tasks(project_id: str) -> str:
    """
    Fetch all pending tasks from the backlog for a specific project.
    """
    with get_db_session() as db:
        result = db.execute(
            text(
                "SELECT id, title, description, status FROM tasks WHERE project_id = :pid AND status = :status"
            ),
            {"pid": project_id, "status": TASK_STATUS_IN_PROGRESS},
        )
        tasks = [
            {
                "id": str(row[0]),
                "title": row[1],
                "description": row[2] or "",
                "status": row[3],
            }
            for row in result
        ]
    return json.dumps(tasks)


@tool
def create_task(
    title: str,
    description: str,
    project_id: str,
    type: str,
    priority: str = "normal",
    tags: Optional[List[str]] = None,
) -> str:
    """
    Create a new task in the backlog.
    Type should be blocker_resolution, risk_mitigation, or action_item.
    """
    with get_db_session() as db:
        db.execute(
            text("""
                INSERT INTO tasks (
                    deleted_at, project_id, id, created_at, updated_at, deadline, 
                    status, description, title, category, label, priority, complexity
                ) VALUES (
                    NULL, :pid, gen_random_uuid(), :now, :now, NULL, 
                    :status, :desc, :title, :cat, 1, :priority, 'medium'
                )
            """),
            {
                "pid": project_id,
                "now": datetime.now(timezone.utc),
                "status": TASK_STATUS_TODO,
                "desc": f"[{type.upper()}] {description} (Tags: {','.join(tags or [])})",
                "title": title,
                "cat": TASK_CATEGORY_BACKEND,
                "priority": TASK_PRIORITY_MEDIUM,
            },
        )
        db.commit()
    return f"Created task: {title}"


@tool
def update_task(task_id: str, changes: List[str]) -> str:
    """
    Update an existing task with links to blockers/action items and priority upgrades.
    """
    with get_db_session() as db:
        db.execute(
            text(
                "UPDATE tasks SET updated_at = :now, description = description || :log WHERE id = :id"
            ),
            {
                "now": datetime.now(timezone.utc),
                "log": f"\n[Update Log] {'; '.join(changes)}",
                "id": task_id,
            },
        )
        db.commit()
    return f"Updated task {task_id}"


@tool
def match_participant_by_domain(domain_tags: List[str], project_id: str) -> str:
    """
    Find a project member that matches the domain tags (role, tags).
    Returns matched candidates list.
    """
    backgrounds = {
        DOMAIN_MAPPING.get(tag.lower())
        for tag in domain_tags
        if tag.lower() in DOMAIN_MAPPING
    }
    backgrounds.discard(None)

    with get_db_session() as db:
        if backgrounds:
            bg_target = list(backgrounds)[0]
            result = db.execute(
                text(
                    "SELECT pm.id, u.name, u.email FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id = :pid AND pm.background = :bg"
                ),
                {"pid": project_id, "bg": bg_target},
            )
        else:
            result = db.execute(
                text(
                    "SELECT pm.id, u.name, u.email FROM project_members pm JOIN users u ON pm.user_id = u.id WHERE pm.project_id = :pid"
                ),
                {"pid": project_id},
            )

        members = [
            {"id": str(row[0]), "name": row[1], "email": row[2]} for row in result
        ]
    return json.dumps(members)


@tool
def log_risk(description: str, likelihood: str, impact: str) -> str:
    """Log a risk to the Risk Register."""
    logger.info(
        f"RISK LOGGED: {description} (Likelihood: {likelihood}, Impact: {impact})"
    )
    return "Risk Logged successfully."


@tool
def flag_for_review(reason: str) -> str:
    """Flag a task/assignment decision for human review."""
    logger.warning(f"FLAGGED FOR REVIEW: {reason}")
    return "Flagged for human review."
