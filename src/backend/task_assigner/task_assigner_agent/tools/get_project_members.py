from langchain.tools import tool
from src.backend.db.database import SessionLocal
from src.backend.model.project import ProjectMember
from src.backend.model.user_detail import UserDetail
from uuid import UUID


def make_get_project_members_tool(project_id: UUID):
    @tool
    def get_project_members() -> str:
        """Fetch all project members with their skills, background, and designations."""
        db = SessionLocal()
        try:
            members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()

            if not members:
                return "No members found for this project."

            result = []
            for m in members:
                details = db.query(UserDetail).filter(UserDetail.user_id == m.user_id).first()
                # Fetch current workload (count of incomplete tasks)
                from src.backend.model.task import Task, TaskStatus
                workload = db.query(Task).filter(
                    Task.project_member_id == m.id,
                    Task.status != TaskStatus.COMPLETED,
                    Task.deleted_at.is_(None)
                ).count()

                detail_str = (
                    f"Skills: {details.skills}, Exp: {details.experience_years}, Desig: {details.designation}"
                    if details else "No details found"
                )
                result.append(
                    f"MemberID: {m.id}, UserID: {m.user_id}, Background: {m.background}, "
                    f"Workload: {workload} active tasks, {detail_str}"
                )

            return "\n".join(result)
        finally:
            db.close()

    return get_project_members
