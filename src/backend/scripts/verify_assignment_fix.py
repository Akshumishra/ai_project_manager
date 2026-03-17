import sys
import os
import uuid
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User

def verify_assignment_attribution():
    db = SessionStandup()
    try:
        # 1. Setup - Find AI Project Manager project and members
        project = db.query(Project).filter(Project.name.ilike("%AI Project Manager%")).first()
        if not project:
            print("Project 'AI Project Manager' not found.")
            return

        aarushi = db.query(ProjectMember).join(User).filter(
            ProjectMember.project_id == project.id,
            User.name.ilike("%Aarushi%")
        ).first()
        akshita = db.query(ProjectMember).join(User).filter(
            ProjectMember.project_id == project.id,
            User.name.ilike("%Akshita%")
        ).first()

        if not aarushi or not akshita:
            print(f"Members not found. Aarushi: {aarushi is not None}, Akshita: {akshita is not None}")
            return

        print(f"Aarushi Slack ID: {aarushi.slack_id}")
        print(f"Akshita Slack ID: {akshita.slack_id}")

        # 2. Create a test standup
        standup = Standup(
            id=uuid.uuid4(),
            project_id=project.id,
            slack_channel_id="C_VERIFY",
            message_ts="ts_verify_" + str(uuid.uuid4())[:8],
            created_at=datetime.now()
        )
        db.add(standup)
        db.flush()
        print(f"Created Test Standup: {standup.id}")

        # 3. Mock Slack response with a mention
        manager = StandupManager(db)
        
        # Monkeypatch list_replies
        def mock_list_replies(channel, thread_ts):
            return [
                {"user": "BOT", "text": "Standup Start", "ts": thread_ts},
                {"user": aarushi.slack_id, "text": f"<@{akshita.slack_id}> implement unit tests.", "ts": "1773566227.910499"}
            ]
        manager.slack_service.list_replies = mock_list_replies

        # 4. Process replies
        print("\n--- Processing Replies ---")
        manager.process_new_replies(str(standup.id))

        # 5. Verify StandupUpdate and ActionLogs
        update = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup.id).first()
        if not update:
            print("FAILED: No StandupUpdate record created.")
            return
            
        print(f"Processed Update Text: '{update.reply_text}'")
        
        from src.backend.model.standup_action_log import StandupActionLog
        action_logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == update.id).all()
        print("\nAction Logs Created:")
        for log in action_logs:
            print(f" - {log.action_taken}")

        # 6. Finalize and check summary
        def mock_post(channel, text, thread_ts=None):
            print(f"\n--- FINAL SUMMARY CAPTURED ---\n{text}\n---------------------------")
            return "final_ts"
        manager.slack_service.post_message = mock_post
        
        print("\n--- Finalizing Standup ---")
        manager.finalize_standup(str(standup.id))

        # 7. Check if Akshita has a new task
        from src.backend.model.task import Task
        new_task = db.query(Task).filter(
            Task.project_id == project.id,
            Task.project_member_id == akshita.id,
            Task.name.ilike("%unit tests%")
        ).first()
        
        if new_task:
            print(f"\nSUCCESS: Task '{new_task.name}' assigned to {akshita.user.name}")
        else:
            print("\nFAILED: Task not assigned to Akshita.")

        db.rollback() # Don't persist test data
        print("\nVerification complete (rolled back).")

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    verify_assignment_attribution()
