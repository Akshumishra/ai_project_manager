"""
Debug script to check why standup summary isn't appearing.
Run this after calling /process and before /finalize to see what data exists.
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.user import User

def debug_standup(standup_id: str):
    """Debug a standup to see what data exists."""
    db = SessionStandup()
    
    try:
        # Convert string to UUID if needed
        try:
            standup_uuid = uuid.UUID(standup_id)
        except ValueError:
            print(f"❌ Invalid UUID format: {standup_id}")
            return
        
        standup = db.query(Standup).filter(Standup.id == standup_uuid).first()
        if not standup:
            print(f"❌ Standup {standup_id} not found!")
            return
        
        print(f"📋 Standup ID: {standup_id}")
        print(f"   Project ID: {standup.project_id}")
        print(f"   Channel: {standup.slack_channel_id}")
        print(f"   Message TS: {standup.message_ts}")
        print(f"   Summary in DB: {'Yes' if standup.summary else 'No'}")
        if standup.summary:
            print(f"   Summary preview: {standup.summary[:100]}...")
        print()
        
        # Check updates
        updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == standup.id).all()
        print(f"📝 Updates found: {len(updates)}")
        
        if not updates:
            print("   ⚠️  No updates found! Make sure you:")
            print("      1. Replied to the standup thread in Slack")
            print("      2. Called /standup/process/{standup_id} API")
            print()
            return
        
        for i, update in enumerate(updates, 1):
            user = db.query(User).get(update.user_id)
            user_name = user.name if user else "Unknown"
            print(f"   Update {i}:")
            print(f"      User: {user_name}")
            print(f"      Reply text: {update.reply_text[:100]}...")
            print(f"      Slack TS: {update.slack_ts}")
            
            # Check action logs
            action_logs = db.query(StandupActionLog).filter(
                StandupActionLog.update_id == update.id
            ).all()
            print(f"      Action logs: {len(action_logs)}")
            
            if not action_logs:
                print("      ⚠️  No action logs! The AI agent may not have parsed the reply.")
            else:
                for log in action_logs:
                    print(f"         - {log.action_taken}")
            print()
        
        # Summary generation check
        print("🔍 Summary Generation Check:")
        summary_updates = []
        all_blockers = []
        
        for update in updates:
            user = db.query(User).get(update.user_id)
            user_name = user.name if user else "Unknown"
            
            action_logs = db.query(StandupActionLog).filter(
                StandupActionLog.update_id == update.id
            ).all()
            
            for log in action_logs:
                if "Updated task" in log.action_taken:
                    summary_updates.append({
                        "user": user_name,
                        "task": log.action_taken.split("Updated task ")[1].split(" status to")[0],
                        "status": log.action_taken.split("status to ")[1]
                    })
                elif "BLOCKER (" in log.action_taken:
                    blocker_detail = log.action_taken.split(": ", 1)[1]
                    all_blockers.append(f"{user_name}: {blocker_detail}")
                elif "CREATED NEW TASK" in log.action_taken:
                    task_part = log.action_taken.split("CREATED NEW TASK: ")[1] if ": " in log.action_taken else log.action_taken.replace("CREATED NEW TASK", "").strip()
                    summary_updates.append({
                        "user": user_name,
                        "task": task_part,
                        "status": "newly created"
                    })
        
        print(f"   Summary updates: {len(summary_updates)}")
        print(f"   Blockers: {len(all_blockers)}")
        
        if summary_updates:
            print("   Updates that will appear in summary:")
            for up in summary_updates:
                print(f"      - {up['user']}: {up['task']} ({up['status']})")
        else:
            print("   ⚠️  No summary updates found! Summary will show 'No updates were recorded'")
        
        if all_blockers:
            print("   Blockers that will appear in summary:")
            for blocker in all_blockers:
                print(f"      - {blocker}")
        
        print()
        print("💡 Next steps:")
        if not updates:
            print("   1. Reply to the standup thread in Slack")
            print("   2. Call POST /standup/process/{standup_id}")
        elif not any(db.query(StandupActionLog).filter(StandupActionLog.update_id == u.id).all() for u in updates):
            print("   1. Check if your reply was parsed correctly by the AI agent")
            print("   2. Check server logs for any errors during processing")
        else:
            print("   1. Call POST /standup/finalize/{standup_id}")
            print("   2. Check server logs for any Slack API errors")
            print("   3. Verify SLACK_BOT_TOKEN is set correctly")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 debug_standup_summary.py <standup_id>")
        print("\nTo find standup_id:")
        print("  1. Check the database: SELECT id, project_id, message_ts FROM standups;")
        print("  2. Or check server logs when you trigger a standup")
        sys.exit(1)
    
    standup_id = sys.argv[1]
    debug_standup(standup_id)
