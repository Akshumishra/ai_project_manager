from langchain.tools import tool
from src.backend.db.database import SessionLocal
from src.backend.model.task import Task, TaskPriority
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import desc


def make_assign_task_tool():
    @tool
    def assign_task(task_id: str, member_id: str, priority: str) -> str:
        """Assign a task with priority. Deadline is auto-calculated."""

        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == UUID(task_id)).first()
            if not task:
                return f"Task {task_id} not found."

            # ✅ SET PRIORITY
            try:
                task.priority = TaskPriority(priority.lower())
            except:
                task.priority = TaskPriority.MEDIUM

            task.project_member_id = UUID(member_id)

            # ✅ ESTIMATE DAYS BASED ON PRIORITY + COMPLEXITY
            base_days = {
                "low": 2,
                "medium": 4,
                "high": 7
            }

            complexity_multiplier = {
                "low": 1,
                "medium": 1.5,
                "high": 2
            }

            est_days = int(
                base_days[task.priority.value] *
                complexity_multiplier[task.complexity.value]
            )

            # ✅ GET LAST TASK DEADLINE (CHAINING)
            last_task = db.query(Task).filter(
                Task.project_member_id == UUID(member_id),
                Task.deadline.isnot(None)
            ).order_by(desc(Task.deadline)).first()

            start_time = last_task.deadline if last_task else datetime.utcnow()

            # ✅ FINAL DEADLINE = previous + est_days + 2 buffer
            deadline = start_time + timedelta(days=est_days + 2)

            task.deadline = deadline

            db.commit()

            return (
                f"Task '{task.title}' assigned.\n"
                f"Priority: {task.priority.value}\n"
                f"Estimated days: {est_days}\n"
                f"Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}"
            )

        except Exception as e:
            db.rollback()
            return f"Error: {str(e)}"
        finally:
            db.close()

    return assign_task