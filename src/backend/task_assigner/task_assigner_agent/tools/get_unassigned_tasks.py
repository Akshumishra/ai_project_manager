from langchain.tools import tool
from src.backend.db.database import SessionLocal
from src.backend.model.task import Task
from uuid import UUID


def make_get_unassigned_tasks_tool(project_id: UUID):
    @tool
    def get_unassigned_tasks() -> str:
        """Fetch all tasks that are currently not assigned to any project member."""
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.project_id == project_id,
                Task.project_member_id == None,
                Task.deleted_at.is_(None)
            ).all()

            if not tasks:
                return "No unassigned tasks found for this project."

            result = []
            for task in tasks:
                result.append(
                    f"ID: {task.id}, Title: {task.title}, Label: {task.label}, "
                    f"Category: {task.category}, Priority: {task.priority}, Complexity: {task.complexity}"
                )

            return "\n".join(result)
        finally:
            db.close()

    return get_unassigned_tasks
