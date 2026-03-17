import sys
import os
import uuid
import json
import re
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User

def simulate_process():
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
            
        print(f"--- Simulating process_new_replies for Standup: {standup.id} ---")
        
        manager = StandupManager(db)
        replies = manager.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
        
        print(f"Found {len(replies)} replies (including prompt).")
        
        for reply in replies[1:]:
            user_slack_id = reply.get("user")
            raw_text = reply.get("text", "")
            reply_ts = reply.get("ts")
            print(f"\nEvaluating reply from {user_slack_id} at {reply_ts}")

            # Cleaning logic from standup_manager.py
            text = re.sub(r'<@U[A-Z0-9]+>', '', raw_text)
            text = re.sub(r'[*_]{1,2}', '', text)
            text = text.strip()
            print(f"  - Cleaned Text: '{text}'")

            # Existence check
            existing = db.query(StandupUpdate).filter(
                StandupUpdate.standup_id == standup.id
            ).filter(
                (StandupUpdate.slack_ts == reply_ts) | (StandupUpdate.reply_text == text)
            ).first()
            
            if existing:
                print(f"  - SKIPPING: Already exists (ID: {existing.id})")
                continue

            try:
                # Identify member
                member = db.query(ProjectMember).filter(
                    ProjectMember.project_id == standup.project_id,
                    ProjectMember.slack_id == user_slack_id
                ).first()
                
                if not member:
                    print(f"  - SKIPPING: Member not found for Slack ID {user_slack_id}")
                    continue

                print(f"  - Member Found: {member.user_id}")
                
                # Fetch active tasks
                active_tasks = manager.generator.fetch_active_tasks(str(standup.project_id))
                user = db.query(User).get(member.user_id)
                user_name = user.name if user else "Developer"
                print(f"  - User: {user_name}")

                flat_tasks = []
                for m_tasks in active_tasks.values():
                    flat_tasks.extend(m_tasks)

                # Date calculation
                msg_date = None
                if reply_ts:
                    msg_date = datetime.fromtimestamp(float(reply_ts), tz=timezone.utc)
                print(f"  - Message Date: {msg_date}")

                # AI Parsing
                print("  - Parsing with agent...")
                parsed = manager.agent.parse_reply(user_name, text, flat_tasks, message_date=msg_date)
                print(f"  - Parsed: {parsed}")

                # Save Update
                update = StandupUpdate(
                    standup_id=standup.id,
                    user_id=member.user_id,
                    reply_text=text,
                    slack_ts=reply_ts
                )
                db.add(update)
                db.flush()
                print(f"  - Created Update record: {update.id}")

                # Apply updates
                print("  - Applying updates...")
                manager._apply_parsed_updates(update.id, parsed)
                print("  - Updates applied.")

                db.commit()
                print("  - SUCCESS: Committed.")

            except Exception as e:
                print(f"  - ERROR: {e}")
                import traceback
                traceback.print_exc()
                db.rollback()

    except Exception as e:
        print(f"Top-level ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simulate_process()
