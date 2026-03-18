import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.db.database import SessionLocal
from src.backend.db.database_standup import SessionStandup
from src.backend.model.task import Task, TaskStatus, TaskPriority, TaskComplexity, TaskCategory
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User

def seed_suggestions_test():
    # Try SessionStandup first as it's what the standup manager uses
    db = SessionStandup()
    try:
        # 1. Get a project
        project = db.query(Project).first()
        if not project:
            print("⚠️ No project found in SessionStandup. Trying SessionLocal...")
            db.close()
            db = SessionLocal()
            project = db.query(Project).first()
            
        if not project:
            print("❌ No project found in any session. Please run individual setup or migrations first.")
            return
        
        print(f"🌱 Seeding data for project: {project.name} ({project.id})")

        # 2. Get members
        members = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
        if not members:
            print(f"❌ No members found for project {project.name}.")
            return

        # 3. Choose a member to be "idle"
        # We'll try to target 'Aarushi' first, otherwise the first member
        idle_member = None
        for m in members:
            u = db.query(User).get(m.user_id)
            if u and u.name == "Aarushi":
                idle_member = m
                break
        
        if not idle_member:
            idle_member = members[0]
            
        user = db.query(User).get(idle_member.user_id)
        print(f"👤 Target idle member: {user.name if user else 'Unknown'}")

        # 4. Clear existing non-completed tasks for this member to ensure they are idle
        deleted_count = db.query(Task).filter(
            Task.project_id == project.id,
            Task.project_member_id == idle_member.id,
            Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
        ).delete(synchronize_session=False)
        print(f"🗑️ Deleted {deleted_count} active tasks for {user.name} to make them idle.")

        # 5. Add some TODO tasks for this member
        todo_tasks = [
            {"title": "Refactor API documentation", "priority": TaskPriority.MEDIUM},
            {"title": "Setup CI/CD pipeline", "priority": TaskPriority.HIGH},
            {"title": "Write unit tests for Auth", "priority": TaskPriority.LOW},
        ]

        for i, t in enumerate(todo_tasks):
            new_task = Task(
                project_id=project.id,
                title=t["title"],
                description=f"Description for {t['title']}",
                status=TaskStatus.TODO,
                priority=t["priority"],
                complexity=TaskComplexity.MEDIUM,
                category=TaskCategory.BACKEND,
                project_member_id=idle_member.id,
                deadline=datetime.now(timezone.utc) + timedelta(days=i+1)
            )
            db.add(new_task)
            print(f"✅ Added TODO task: {t['title']} assigned to {user.name}")

        # 6. Add some unassigned TODO tasks in the project
        unassigned_tasks = [
            {"title": "Research new frontend framework", "priority": TaskPriority.LOW},
            {"title": "Optimize database queries", "priority": TaskPriority.HIGH},
        ]

        for i, t in enumerate(unassigned_tasks):
            new_task = Task(
                project_id=project.id,
                title=t["title"],
                description=f"Description for {t['title']}",
                status=TaskStatus.TODO,
                priority=t["priority"],
                complexity=TaskComplexity.MEDIUM,
                category=TaskCategory.BACKEND,
                project_member_id=None,
                deadline=datetime.now(timezone.utc) + timedelta(days=i+5)
            )
            db.add(new_task)
            print(f"✅ Added unassigned TODO task: {t['title']}")

        db.commit()
        print("\n✨ Seeding complete! You can now run the standup trigger to see suggestions.")
        print(f"Run: python src/backend/scripts/test_scheduler_jobs.py")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_suggestions_test()
