from langchain.tools import tool
from src.backend.db.database import get_session_local
from src.backend.model.task import Task, TaskPriority, TaskComplexity
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import desc

def make_assign_task_tool():
    @tool
    def assign_task(task_id: str, member_id: str, priority: str = "medium") -> str:
        """Assign a task with automatic deadline calculation based on priority and current workload."""
        db = get_session_local()()
        try:
            task = db.query(Task).filter(Task.id == UUID(task_id)).first()
            if not task:
                return f"Task {task_id} not found."

            # 1. Update Member and Priority
            task.project_member_id = UUID(member_id)
            try:
                task.priority = TaskPriority(priority.lower())
            except:
                task.priority = TaskPriority.MEDIUM

            # 2. Calculate task duration based on complexity and priority
            # Base days (Low: 2, Medium: 4, High: 7)
            base_days = {
                TaskPriority.LOW: 2,
                TaskPriority.MEDIUM: 4,
                TaskPriority.HIGH: 7
            }
            # Multiplier (Low: 1.0, Medium: 1.5, High: 2.0)
            mult = {
                TaskComplexity.LOW: 1.0,
                TaskComplexity.MEDIUM: 1.5,
                TaskComplexity.HIGH: 2.0
            }

            days_needed = int(base_days[task.priority] * mult.get(task.complexity, 1.5))
            
            # 3. Workload Chaining
            # Find the latest deadline among already assigned tasks for this member
            last_task = db.query(Task).filter(
                Task.project_member_id == UUID(member_id),
                Task.deadline.isnot(None),
                Task.id != task.id  # Don't compare with self
            ).order_by(desc(Task.deadline)).first()

            # Start the new task after the last one, or from now
            start_time = last_task.deadline if last_task else datetime.utcnow()
            
            # Add duration + 2 days of buffer
            deadline = start_time + timedelta(days=days_needed + 2)
            task.deadline = deadline

            db.commit()
            
            return (
                f"Task '{task.title}' assigned to {member_id}.\n"
                f"Priority: {task.priority.value}, Complexity: {task.complexity.value}\n"
                f"Estimated Duration: {days_needed} days (+2 days buffer).\n"
                f"Calculated Deadline: {deadline.strftime('%Y-%m-%d %H:%M')} "
                f"(Scheduled after {last_task.title if last_task else 'today'})"
            )

        except Exception as e:
            db.rollback()
            return f"Error highlighting assignment issues: {str(e)}"
        finally:
            db.close()

    return assign_task