import sys
import os
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.project import Project, ProjectMember

def verify_historical_context():
    # Use owner credentials to setup test data
    engine = create_engine(Config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("--- Starting Historical Context Verification ---")
        
        # 1. Get test member
        member = db.query(ProjectMember).first()
        if not member:
            print("Error: No ProjectMember found.")
            return
            
        project_id = member.project_id
        user_id = member.user_id

        # 2. Simulate a PREVIOUS completed standup
        print("Step 1: Creating a historical standup session...")
        prev_standup = Standup(
            project_id=project_id,
            slack_channel_id="C12345",
            message_ts="prev_123.456",
            summary="Completed yesterday's tasks."
        )
        db.add(prev_standup)
        db.flush()

        # Add a reply and action log
        update = StandupUpdate(
            standup_id=prev_standup.id,
            user_id=user_id,
            reply_text="I fixed the login bug. It was a race condition. Blocking issue with SSL resolved."
        )
        db.add(update)
        db.flush()

        blocker_log = StandupActionLog(
            update_id=update.id,
            action_taken="BLOCKER DETECTED: SSL Configuration"
        )
        db.add(blocker_log)
        db.commit()

        # 3. Mock Slack and Initiate NEW standup
        with patch('src.backend.services.slack_service.requests.post') as mock_post:
            mock_post.return_value.json.return_value = {"ok": True, "ts": "new_999.000"}
            mock_post.return_value.status_code = 200
            
            manager = StandupManager(db)
            manager.db = db
            manager.generator.db = db
            
            print("Step 2: Initiating a NEW standup to see if it fetches history...")
            # This should call _get_historical_highlights internally
            ts = manager.initiate_standup(str(project_id), "C12345")
            
            # Use the capture of the call to check the prompt text
            # mock_post is called in slack_service.post_message
            args, kwargs = mock_post.call_args
            prompt_text = kwargs['json']['text']
            
            print("\n--- Generated Prompt Preview ---")
            print(prompt_text)
            print("--------------------------------\n")
            
            if "Highlights from last Standup" in prompt_text and "SSL Configuration" in prompt_text:
                print("SUCCESS: Historical highlights correctly included in the prompt!")
            else:
                print("FAILURE: Historical highlights missing or incorrect.")

    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup test data? Maybe just leave it as it's a test DB
        db.close()

if __name__ == "__main__":
    verify_historical_context()
