
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.model.task import Task, TaskStatus

# Database setup
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def seed_recrude_tasks():
    print("🌱 Seeding initial tasks for 'recrude' (Fixed Model)...")
    
    project = db.query(Project).filter(Project.name == "recrude").first()
    if not project:
        print("❌ Project 'recrude' not found.")
        return

    # Get ProjectMember IDs
    members = {m.user.name: m.id for m in db.query(ProjectMember).join(User).filter(
        ProjectMember.project_id == project.id,
        User.name.in_(["Aarushi", "Akshita"])
    ).all()}
    
    tasks = [
        Task(
            project_id=project.id,
            title="Setup Recruitment Pipeline", label=1,
            description="Define the stages for the applicant tracking system.",
            status=TaskStatus.IN_PROGRESS,
            assignee_id=members.get("Aarushi"),
            deadline=datetime.now(timezone.utc) + timedelta(days=7)
        ),
        Task(
            project_id=project.id,
            title="Design Landing Page Mockups", label=2,
            description="Create high-fidelity mockups for the landing page.",
            status=TaskStatus.TODO,
            assignee_id=members.get("Akshita"),
            deadline=datetime.now(timezone.utc) + timedelta(days=3)
        ),
        Task(
            project_id=project.id,
            title="Implement Authentication API", label=3,
            description="Build the JWT-based auth flow for recrude.",
            status=TaskStatus.TODO,
            assignee_id=members.get("Aarushi"),
            deadline=datetime.now(timezone.utc) + timedelta(days=5)
        )
    ]
    
    db.add_all(tasks)
    db.commit()
    print(f"✅ Successfully seeded {len(tasks)} tasks for 'recrude'.")

if __name__ == "__main__":
    try:
        seed_recrude_tasks()
    except Exception as e:
        print(f"❌ Error seeding tasks: {e}")
        db.rollback()
    finally:
        db.close()
