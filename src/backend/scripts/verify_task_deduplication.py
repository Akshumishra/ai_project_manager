
import os
import sys
import uuid
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.services.standup_manager import StandupManager
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.agents.standup_agent import StandupParsedResponse, TaskUpdate, NewTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_manager_db"

def verify_deduplication():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Setup context
        project_name = "AI Project Manager"
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            print(f"❌ Project {project_name} not found")
            return

        # Find Aarushi (who mentioned the task in the prompt)
        user = db.query(User).filter(User.name == "Aarushi").first()
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id
        ).first()

        task_name = "Sprint Planning & Backlog Grooming"
        
        # Check initial state
        initial_tasks = db.query(Task).filter(
            Task.project_id == project.id,
            Task.project_member_id == member.id,
            Task.name == task_name
        ).all()
        
        print(f"Initial tasks found with name '{task_name}': {len(initial_tasks)}")
        for t in initial_tasks:
            print(f"  - ID: {t.id}, Status: {t.status.value}")

        if not initial_tasks:
            print("❌ No initial task found to test with. Please run seeding first.")
            return

        # 2. Create a dummy standup and update record
        standup = Standup(
            project_id=project.id,
            slack_channel_id="CTEST",
            message_ts="123456.789"
        )
        db.add(standup)
        db.flush()

        update = StandupUpdate(
            standup_id=standup.id,
            user_id=user.id,
            reply_text="I started sprint planning",
            slack_ts="123456.999"
        )
        db.add(update)
        db.flush()

        # 3. Simulate AI response where task_id is missing (the problematic case)
        # Case A: AI identifies it as an update but misses the ID
        parsed_a = StandupParsedResponse(
            updates=[
                TaskUpdate(
                    task_id=None,
                    task_name=task_name,
                    new_status="inprogress",
                    comment="Started the work"
                )
            ],
            sentiment="positive"
        )

        manager = StandupManager(db)
        print("\n--- Testing Deduplication Fallback in _apply_parsed_updates ---")
        manager._apply_parsed_updates(update.id, parsed_a)
        
        # Verify
        db.flush()
        final_tasks = db.query(Task).filter(
            Task.project_id == project.id,
            Task.project_member_id == member.id,
            Task.name == task_name
        ).all()
        
        print(f"Final tasks found with name '{task_name}': {len(final_tasks)}")
        for t in final_tasks:
            print(f"  - ID: {t.id}, Status: {t.status.value}")

        if len(final_tasks) == len(initial_tasks):
            print("✅ SUCCESS: No duplicate task created. Status updated on existing task.")
        else:
            print(f"❌ FAILURE: Task count changed from {len(initial_tasks)} to {len(final_tasks)}")

        db.rollback() # Clean up test data
        print("Test data rolled back.")

    finally:
        db.close()

if __name__ == "__main__":
    verify_deduplication()
