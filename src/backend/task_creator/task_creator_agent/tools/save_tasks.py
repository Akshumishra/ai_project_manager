import logging
from typing import List, Dict, Any
from sqlalchemy import func
from uuid import UUID
from langchain.tools import tool
from sqlalchemy.orm import Session

from src.backend.db.database import SessionLocal
from src.backend.model.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskComplexity

logger = logging.getLogger(__name__)

def make_save_tasks_tool(user_id: UUID, project_id: UUID):
    """
    Factory function to create a tool for saving tasks to the database.
    """
    
    @tool("save_tasks")
    def save_tasks(tasks: List[Dict[str, Any]]) -> str:
        """
        Saves a list of generated tasks to the database for a specific project.
        'tasks' should be a list of objects with title, description, priority, complexity, and category.
        """
        db = SessionLocal()
        try:
            # Get current max label for this project
            max_label = db.query(func.max(Task.label)).filter(Task.project_id == project_id).scalar()
            base_label = (max_label or 0)
            
            created_count = 0
            for i, item in enumerate(tasks):
                # Map category
                cat_str = item.get("category", "backend").lower()
                try:
                    category = TaskCategory(cat_str)
                except ValueError:
                    if "backend" in cat_str: category = TaskCategory.BACKEND
                    elif "frontend" in cat_str: category = TaskCategory.FRONTEND
                    elif "database" in cat_str: category = TaskCategory.DATABASE
                    elif "ai" in cat_str or "ml" in cat_str: category = TaskCategory.AI_ML
                    elif "devops" in cat_str: category = TaskCategory.DEVOPS
                    elif "qa" in cat_str or "test" in cat_str: category = TaskCategory.QA
                    elif "security" in cat_str: category = TaskCategory.SECURITY
                    else: category = TaskCategory.BACKEND

                # Map priority
                prio_str = item.get("priority", "medium").lower()
                try:
                    priority = TaskPriority(prio_str)
                except ValueError:
                    priority = TaskPriority.MEDIUM

                # Map complexity
                comp_str = item.get("complexity", "medium").lower()
                try:
                    complexity = TaskComplexity(comp_str)
                except ValueError:
                    complexity = TaskComplexity.MEDIUM

                new_task = Task(
                    title=item.get("title", "Untitled Task"),
                    label=base_label + created_count + 1,
                    description=item.get("description", ""),
                    project_id=project_id,
                    category=category,
                    priority=priority,
                    complexity=complexity,
                    status=TaskStatus.TODO,
                    project_member_id=None
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
