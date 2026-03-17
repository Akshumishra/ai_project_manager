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

def diagnostic_process():
    db = SessionStandup()
    try:
        # Find AI Tutor project
        project = db.query(Project).filter(Project.name.ilike("%AI Tutor%")).first()
        if not project:
            print("AI Tutor project not found.")
            return
            
        # Find latest standup for this project
        standup = db.query(Standup).filter(Standup.project_id == project.id).order_by(Standup.created_at.desc()).first()
        if not standup:
            print("No standup found for AI Tutor.")
            return
            
        print(f"--- Diagnosing Standup: {standup.id} ---")
        
        manager = StandupManager(db)
        
        # Manually run the processing logic but catch exceptions in detail
        print("\n--- Running process_new_replies logic with debug... ---")
        replies = manager.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
        
        for reply in replies[1:]:
            user_slack_id = reply.get("user")
            raw_text = reply.get("text", "")
            reply_ts = reply.get("ts")
            print(f"\nProcessing reply from {user_slack_id} at {reply_ts}: {raw_text}")

            try:
                # 1. Identify member
                member = db.query(ProjectMember).filter(
                    ProjectMember.project_id == project.id,
                    ProjectMember.slack_id == user_slack_id
                ).first()
                if not member:
                    print(f"  - SKIPPING: Member not found for Slack ID {user_slack_id}")
                    continue

                # 2. Extract structured data
                active_tasks = manager.generator.fetch_active_tasks(str(standup.project_id))
                user = db.query(User).get(member.user_id)
                user_name = user.name if user else "Developer"
                print(f"  - User Name: {user_name}")

                flat_tasks = []
                for m_tasks in active_tasks.values():
                    flat_tasks.extend(m_tasks)

                print("  - Calling agent.parse_reply...")
                parsed = manager.agent.parse_reply(user_name, raw_text, flat_tasks)
                print(f"  - Agent Parsed Data: {parsed}")

                # 3. Save Update
                update = StandupUpdate(
                    standup_id=standup.id,
                    user_id=member.user_id,
                    reply_text=raw_text,
                    slack_ts=reply_ts
                )
                db.add(update)
                db.flush()
                print(f"  - Update record created: {update.id}")

                # 4. Apply Updates
                print("  - Calling _apply_parsed_updates...")
                manager._apply_parsed_updates(update.id, parsed)
                print("  - _apply_parsed_updates completed.")
                
                # Check for action logs
                from src.backend.model.standup_action_log import StandupActionLog
                logs = db.query(StandupActionLog).filter(StandupActionLog.update_id == update.id).all()
                print(f"  - Action logs created: {[l.action_taken for l in logs]}")

                db.commit()
                print("  - COMMIT SUCCESSFUL.")

            except Exception as e:
                print(f"  - ERROR in processing: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()

        # Finalize
        print("\n--- Running finalize_standup logic with debug... ---")
        try:
            # We use a mock post_message to see the final text without posting
            original_post = manager.slack_service.post_message
            captured_summary = []
            def mock_post(channel, text, thread_ts=None):
                captured_summary.append(text)
                return "mock_ts"
            manager.slack_service.post_message = mock_post
            
            manager.finalize_standup(str(standup.id))
            print("\n--- FINAL SUMMARY GENERATED ---")
            if captured_summary:
                print(captured_summary[0])
            else:
                print("No summary was posted.")
            
        except Exception as e:
            print(f"  - ERROR in finalize: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnostic_process()
