from langchain.tools import tool
from src.backend.db.database import SessionLocal
from src.backend.model.task import Task
from uuid import UUID
from datetime import datetime, timedelta


def make_assign_task_tool():
    @tool
    def assign_task(task_id: str, member_id: str, days_to_complete: int) -> str:
        """Assign a task to a member with an estimated number of days to complete."""
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == UUID(task_id)).first()
            if not task:
                return f"Task with ID {task_id} not found."

            task.project_member_id = UUID(member_id)
            # Calculate deadline from current time
            deadline = datetime.utcnow() + timedelta(days=days_to_complete)
            task.deadline = deadline
            db.commit()
            return f"Task '{task.title}' assigned to member {member_id}. Deadline set for {days_to_complete} days from now ({deadline.strftime('%Y-%m-%d %H:%M')})."
        except Exception as e:
            db.rollback()
            return f"Error assigning task: {str(e)}"
        finally:
            db.close()

    return assign_task
