import logging
from typing import List, Dict, Any
from sqlalchemy import func
from uuid import UUID
from langchain.tools import tool
from sqlalchemy.orm import Session
from datetime import datetime

from src.backend.db.database import get_session_local
from src.backend.model.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskComplexity

logger = logging.getLogger(__name__)


def make_save_tasks_tool(user_id: UUID, project_id: UUID):

    @tool("save_tasks")
    def save_tasks(tasks: List[Dict[str, Any]]) -> str:
        """
        Saves a list of generated tasks to the database for a specific project.
        'tasks' should be a list of objects with title, description, priority, complexity, category, deadline, and project_member_id.
        """
        db = get_session_local()()
        try:
            max_label = db.query(func.max(Task.label))\
                .filter(Task.project_id == project_id)\
                .scalar()

            base_label = max_label or 0
            created_count = 0

            for i, item in enumerate(tasks):

                # ✅ TITLE (same as old logic)
                title = item.get("title") or "Untitled Task"

                # ✅ CATEGORY (old flexible mapping logic)
                cat_str = str(item.get("category", "backend")).lower()
                try:
                    category = TaskCategory(cat_str)
                except ValueError:
                    if "backend" in cat_str:
                        category = TaskCategory.BACKEND
                    elif "frontend" in cat_str:
                        category = TaskCategory.FRONTEND
                    elif "database" in cat_str:
                        category = TaskCategory.DATABASE
                    elif "ai" in cat_str or "ml" in cat_str:
                        category = TaskCategory.AI_ML
                    elif "devops" in cat_str:
                        category = TaskCategory.DEVOPS
                    elif "qa" in cat_str or "test" in cat_str:
                        category = TaskCategory.QA
                    elif "security" in cat_str:
                        category = TaskCategory.SECURITY
                    else:
                        category = TaskCategory.BACKEND

                # ✅ PRIORITY (old fallback logic)
                prio_str = str(item.get("priority", "medium")).lower()
                try:
                    priority = TaskPriority(prio_str)
                except ValueError:
                    priority = TaskPriority.MEDIUM

                # ✅ COMPLEXITY (old fallback logic)
                comp_str = str(item.get("complexity", "medium")).lower()
                try:
                    complexity = TaskComplexity(comp_str)
                except ValueError:
                    complexity = TaskComplexity.MEDIUM

                # ✅ DEADLINE (new field support)
                deadline = None
                if item.get("deadline"):
                    try:
                        deadline = datetime.fromisoformat(item["deadline"])
                    except Exception:
                        logger.warning("Invalid deadline format")

                # ✅ ASSIGNEE (new field support)
                project_member_id = None
                if item.get("project_member_id"):
                    try:
                        project_member_id = UUID(item["project_member_id"])
                    except Exception:
                        logger.warning("Invalid project_member_id")

                # ✅ CREATE TASK
                new_task = Task(
                    title=title,
                    description=item.get("description", ""),
                    label=base_label + created_count + 1,
                    project_id=project_id,
                    category=category,
                    priority=priority,
                    complexity=complexity,
                    status=TaskStatus.TODO,
                    deadline=deadline,
                    project_member_id=project_member_id
                )

                db.add(new_task)
                created_count += 1

            db.commit()
            return f"Successfully saved {created_count} tasks to the database."

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save tasks: {e}")
            return f"Error saving tasks: {str(e)}"

        finally:
            db.close()

    return save_tasks