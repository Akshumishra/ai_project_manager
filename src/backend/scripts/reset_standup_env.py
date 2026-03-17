
import os
import sys
import uuid
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.task_log import TaskLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"

PROJECT_IDS = {
    "AI Project Manager": "df940dce-e506-4878-b500-c2dba9b15920",
    "AI Tutor": "b1389d5d-c3f9-481d-8749-492d9c559ed5"
}

MEMBER_IDS = {
    "AI Project Manager": {
        "Aarushi": "45ce0f41-3abd-4715-b4a6-a87a6386bbdd",
        "Akshita": "9abfc728-f555-460f-ae8d-099754fcf26d",
        "Rudraksh": "8ee570f6-32d8-4b82-bcf5-5cffbb799026"
    },
    "AI Tutor": {
        "Aarushi": "fb5531a9-cce2-4740-8d20-701107663ded",
        "Akshita": "aaea4a32-78d9-4d3c-a3fb-f4468387a76b",
        "Rudraksh": "d060a7fa-9dbb-4c25-94ac-8889a67bf4f8"
    }
}

def reset_env():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("🧼 Cleaning up standup-related tables...")
        db.execute(text("TRUNCATE TABLE standup_action_logs RESTART IDENTITY CASCADE;"))
        db.execute(text("TRUNCATE TABLE standup_updates RESTART IDENTITY CASCADE;"))
        db.execute(text("TRUNCATE TABLE standups RESTART IDENTITY CASCADE;"))
        db.execute(text("TRUNCATE TABLE task_logs RESTART IDENTITY CASCADE;"))
        
        print("🗑️ Deleting all tasks...")
        db.execute(text("DELETE FROM tasks;"))
        db.commit()

        print("🌱 Seeding fresh tasks...")
        
        now = datetime.now(timezone.utc)
        
        # --- AI Project Manager Tasks ---
        pm_id = PROJECT_IDS["AI Project Manager"]
        pm_members = MEMBER_IDS["AI Project Manager"]
        
        tasks_to_add = [
            # Aarushi
            Task(
                name="Core System Architecture Review",
                project_id=pm_id,
                project_member_id=pm_members["Aarushi"],
                status=TaskStatus.INPROGRESS,
                deadline=now + timedelta(days=2),
                description="Review current architecture for scalability."
            ),
            Task(
                name="Sprint Planning & Backlog Grooming",
                project_id=pm_id,
                project_member_id=pm_members["Aarushi"],
                status=TaskStatus.TODO,
                deadline=now + timedelta(days=5),
                description="Prepare for the upcoming sprint."
            ),
            # Akshita
            Task(
                name="PostgreSQL Schema Optimization",
                project_id=pm_id,
                project_member_id=pm_members["Akshita"],
                status=TaskStatus.INPROGRESS,
                deadline=now + timedelta(days=4),
                description="Optimize indexes and query performance."
            ),
            Task(
                name="API Endpoint Documentation",
                project_id=pm_id,
                project_member_id=pm_members["Akshita"],
                status=TaskStatus.TODO,
                deadline=now + timedelta(days=6),
                description="Document all REST endpoints in Swagger."
            ),
            # Rudraksh
            Task(
                name="End-to-End Testing Suite Setup",
                project_id=pm_id,
                project_member_id=pm_members["Rudraksh"],
                status=TaskStatus.INPROGRESS,
                deadline=now + timedelta(days=3),
                description="Configure Playwright for E2E tests."
            ),
            Task(
                name="Comprehensive Security Audit",
                project_id=pm_id,
                project_member_id=pm_members["Rudraksh"],
                status=TaskStatus.BLOCKED,
                deadline=now + timedelta(days=8),
                description="Audit blocked by missing compliance checklist."
            )
        ]
        
        # --- AI Tutor Tasks ---
        tutor_id = PROJECT_IDS["AI Tutor"]
        tutor_members = MEMBER_IDS["AI Tutor"]
        
        tasks_to_add.extend([
            Task(
                name="Vector Database Integration",
                project_id=tutor_id,
                project_member_id=tutor_members["Aarushi"],
                status=TaskStatus.INPROGRESS,
                deadline=now + timedelta(days=3),
                description="Integrate Pinecone for RAG."
            ),
            Task(
                name="Knowledge Graph Design",
                project_id=tutor_id,
                project_member_id=tutor_members["Akshita"],
                status=TaskStatus.TODO,
                deadline=now + timedelta(days=7),
                description="Design the initial graph schema for educational content."
            ),
            Task(
                name="UI Component Library Development",
                project_id=tutor_id,
                project_member_id=tutor_members["Rudraksh"],
                status=TaskStatus.INPROGRESS,
                deadline=now + timedelta(days=5),
                description="Build reusable tutoring UI components."
            )
        ])

        for t in tasks_to_add:
            db.add(t)
        
        db.commit()
        print(f"✅ Successfully seeded {len(tasks_to_add)} fresh tasks.")

    except Exception as e:
        print(f"❌ Error resetting environment: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_env()
