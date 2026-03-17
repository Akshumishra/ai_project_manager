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

def debug_ai_tutor_standup():
    print(f"STANDUP_DATABASE_URL: {Config.STANDUP_DATABASE_URL}")
    print(f"DATABASE_URL: {Config.DATABASE_URL}")
    
    db = SessionStandup()
    try:
        # Find AI Tutor project
        project = db.query(Project).filter(Project.name.ilike("%AI Tutor%")).first()
        if not project:
            print("AI Tutor project not found.")
            # List all projects
            all_projects = db.query(Project).all()
            print("Available projects:", [p.name for p in all_projects])
            return
            
        print(f"--- Project: {project.name} ({project.id}) ---")
        
        # Find latest standup for this project
        standup = db.query(Standup).filter(Standup.project_id == project.id).order_by(Standup.created_at.desc()).first()
        if not standup:
            print("No standup found for AI Tutor.")
            return
            
        print(f"Latest Standup: {standup.id}")
        print(f"Created At: {standup.created_at}")
        print(f"Channel ID: {standup.slack_channel_id}")
        print(f"Message TS: {standup.message_ts}")
        print(f"Summary in DB: {standup.summary}")
        
        # Check updates in DB
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup.id).all()
        print(f"Updates in DB: {len(updates)}")
        for u in updates:
            user = db.query(User).get(u.user_id)
            print(f"  - Update from {user.name if user else u.user_id}: {u.reply_text} (Slack TS: {u.slack_ts})")

        # Fetch replies from Slack directly
        print("\n--- Slack Replies (via SlackService) ---")
        manager = StandupManager(db)
        try:
            replies = manager.slack_service.list_replies(standup.slack_channel_id, standup.message_ts)
            print(json.dumps(replies, indent=2))
            
            # Re-run simulation of process_new_replies logic
            print("\n--- Identifying Users for Slack Replies ---")
            for reply in replies[1:]:
                user_slack_id = reply.get("user")
                member = db.query(ProjectMember).filter(
                    ProjectMember.project_id == project.id,
                    ProjectMember.slack_id == user_slack_id
                ).first()
                if member:
                    user = db.query(User).get(member.user_id)
                    print(f"  - Found Member: {user.name} for Slack ID {user_slack_id}")
                else:
                    print(f"  - NO Member found for Slack ID {user_slack_id}")

        except Exception as e:
            print(f"Error fetching Slack replies: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_ai_tutor_standup()
