
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.model.blocker import Blocker
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project
from src.backend.model.user import User

# Database setup
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def get_id(query):
    result = db.execute(query).fetchone()
    return result[0] if result else None

def seed_blockers():
    print("🌱 Seeding realistic blocker data (Dynamic IDs)...")
    
    # Clean up
    db.query(Blocker).delete()
    db.commit()
    
    # Dynamic Lookups
    ai_pm = db.query(Project).filter(Project.name == "AI Project Manager").first()
    ai_tutor = db.query(Project).filter(Project.name == "AI Tutor").first()
    
    if not ai_pm or not ai_tutor:
        print("❌ Could not find projects. Please ensure seed_data.py has been run.")
        return

    users = {u.name: u.id for u in db.query(User).all()}
    
    # Task mappings for AI PM
    task_ui = db.query(Task).filter(Task.project_id == ai_pm.id, Task.name.ilike("%UI Component%")).first()
    task_identify = db.query(Task).filter(Task.project_id == ai_pm.id, Task.name.ilike("%Identify%")).first()
    
    # Task mappings for AI Tutor
    task_doc = db.query(Task).filter(Task.project_id == ai_tutor.id, Task.name.ilike("%Doc%")).first()

    now = datetime.now(timezone.utc)
    
    blockers = [
        # AI PM - Rudraksh (Task specific)
        Blocker(
            project_id=ai_pm.id,
            user_id=users.get("Rudraksh"),
            task_id=task_ui.id if task_ui else None,
            reason="Waiting for Figma access from the designer to verify component dimensions.",
            blocked_by="Design Team",
            impact="high",
            created_at=now - timedelta(days=2)
        ),
        # AI PM - Akshita (General)
        Blocker(
            project_id=ai_pm.id,
            user_id=users.get("Akshita"),
            task_id=None,
            reason="The cloud environment is down, cannot deploy any staging builds.",
            blocked_by="IT/DevOps",
            impact="medium",
            created_at=now - timedelta(hours=12)
        ),
        # AI PM - Aarushi (Resolved)
        Blocker(
            project_id=ai_pm.id,
            user_id=users.get("Aarushi"),
            task_id=task_identify.id if task_identify else None,
            reason="Missing API secret for the legacy database.",
            blocked_by="Security Officer",
            impact="low",
            resolved_at=now - timedelta(days=1),
            created_at=now - timedelta(days=3)
        ),
        # AI Tutor - Aarushi (General)
        Blocker(
            project_id=ai_tutor.id,
            user_id=users.get("Aarushi"),
            task_id=None,
            reason="Waiting for the updated course syllabus to plan the AI tutoring modules.",
            blocked_by="Content Team",
            impact="high",
            created_at=now - timedelta(days=1)
        ),
        # AI Tutor - Akshita (Task specific)
        Blocker(
            project_id=ai_tutor.id,
            user_id=users.get("Akshita"),
            task_id=task_doc.id if task_doc else None,
            reason="The documentation tool is currently undergoing maintenance.",
            blocked_by="Third-party tool",
            impact="low",
            created_at=now - timedelta(hours=2)
        )
    ]
    
    db.add_all(blockers)
    
    # Sync statuses
    for b in blockers:
        if b.task_id and not b.resolved_at:
            task = db.query(Task).get(b.task_id)
            if task:
                task.status = TaskStatus.BLOCKED
    
    db.commit()
    print("✅ Successfully seeded 5 blockers dynamically!")

if __name__ == "__main__":
    try:
        seed_blockers()
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()
