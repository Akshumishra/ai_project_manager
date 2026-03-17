import sys
import os
import uuid
import json
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.project import Project

def verify_morning_enhancements():
    db = SessionStandup()
    try:
        # 1. Find AI Project Manager project
        project = db.query(Project).filter(Project.name.ilike("%AI Project Manager%")).first()
        if not project:
            print("Project 'AI Project Manager' not found.")
            return

        print(f"Testing for Project: {project.name} ({project.id})")

        # 2. Setup - Mock StandupManager to capture the prompt
        manager = StandupManager(db)
        
        # We need historical highlights, let's find the latest standup that actually had updates
        last_standup = db.query(Standup).filter(
            Standup.project_id == project.id
        ).order_by(Standup.created_at.desc()).all()
        
        target_standup = None
        for s in last_standup:
            if s.updates:
                target_standup = s
                break
        
        if target_standup:
            print(f"Testing with past standup: {target_standup.id} from {target_standup.created_at}")
            # Temporarily hack the target_standup to look like it's completed for highlight extraction
            # though StandupManager._get_historical_highlights filters for summary.isnot(None)
            # so we should ideally find one WITH a summary or temporarily mock it.
            if not target_standup.summary:
                target_standup.summary = "Mock Summary"
        else:
            print("No past standup with updates found. Blocker test might be limited.")

        # 3. Capture post_message
        captured_prompt = None
        def mock_post_message(channel, text, thread_ts=None):
            nonlocal captured_prompt
            captured_prompt = text
            return "mock_ts_" + str(uuid.uuid4())[:8]
        
        manager.slack_service.post_message = mock_post_message

        # 4. Trigger standup initiation
        print("\n--- Initiating Standup ---")
        ts = manager.initiate_standup(str(project.id), "C_TEST")
        
        if captured_prompt:
            print("\n--- CAPTURED MORNING PROMPT ---")
            print(captured_prompt)
            print("------------------------------")
            
            # Check for critical section
            if "CRITICAL: Deadline Risks Identified" in captured_prompt:
                print("\nSUCCESS: Critical Section (Deadline Risks) found in prompt.")
            else:
                print("\nFAILED: Critical Section (Deadline Risks) NOT found.")
                
            # Check for historical insights/blockers
            if "Key Insights" in captured_prompt:
                print("SUCCESS: Historical insights section found.")
            if "Member Blockers" in captured_prompt:
                print("SUCCESS: Member Blockers section found.")
            
            if "Key Insights" not in captured_prompt and "Member Blockers" not in captured_prompt:
                print("NOTE: No historical sections found.")
        else:
            print("FAILED: No prompt captured.")

        db.rollback() # Don't record this test standup

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    verify_morning_enhancements()
