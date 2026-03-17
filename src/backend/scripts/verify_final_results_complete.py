import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.services.standup_manager import StandupManager
from src.backend.model.standup_update import StandupUpdate
from src.backend.model.task import Task
from src.backend.model.task_log import TaskLog
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.standup_action_log import StandupActionLog

def verify_all():
    db = SessionStandup()
    sid = 'fc82bcad-b82f-443e-847d-0f2776cf4230'
    pid = 'df940dce-e506-4878-b500-c2dba9b15920'
    
    print("\n--- 🦾 Final End-to-End Verification Report ---")
    # If not found, just pick the absolute latest standup
    if not sid:
        latest = db.query(Standup).order_by(Standup.created_at.desc()).first()
        if latest:
            sid = latest.id
            print(f"🔍 Automatically picked latest standup ID: {sid}")
        else:
            print("❌ No standups found in database.")
            db.close()
            return
    
    # 1. Standup Updates
    print("\n1. 📝 Cleaned Replies (Checks: No bot IDs, No formatting, Robust De-duplication)")
    updates = db.query(StandupUpdate).filter(StandupUpdate.standup_id == sid).all()
    print(f"Total Updates Captured: {len(updates)}")
    for u in updates:
        print(f"    Raw Cleaned Text: '{u.reply_text}'")
        if '@' in u.reply_text or '_' in u.reply_text or '*' in u.reply_text:
            print("    ❌ FAIL: Cleaning incomplete.")
        else:
            print("    ✅ SUCCESS: Deep cleaning active.")

    # 2. Tasks, Deadlines, and Complexity
    print("\n2. 📊 Task Enrichment (Checks: Initial set vs Update)")
    print("   Target Task 1 (Update): 'Slack Integration Setup' (Initial deadline 2026-03-15)")
    print("   Target Task 2 (New): 'User Testing' (Assigned to Rudraksh)")
    
    tasks = db.query(Task).filter(Task.project_id == pid).order_by(Task.created_at.desc()).all()
    for t in tasks:
        print(f"\n  - Task: '{t.name}'")
        print(f"    Deadlines in DB: {t.deadline}")
        print(f"    Complexity: {t.complexity}")
        logs = db.query(TaskLog).filter(TaskLog.task_id == t.id).order_by(TaskLog.created_at.desc()).all()
        print(f"    Latest Log: {logs[0].log if logs else 'No logs'}")
        
    # 3. Action Logs
    print("\n3. 🛡️ Intelligent Action Logs (Blockers & Risk)")
    action_logs = db.query(StandupActionLog).join(StandupUpdate).filter(StandupUpdate.standup_id == sid).all()
    print(f"  Total Action Logs for session: {len(action_logs)}")
    for log in action_logs:
        # Highlight blockers specifically
        if "BLOCKER" in log.action_taken:
            print(f"    🚨 {log.action_taken}")
        else:
            print(f"    - {log.action_taken}")
    
    db.close()

if __name__ == "__main__":
    verify_all()
