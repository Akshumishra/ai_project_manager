
import os
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.blocker import Blocker
from src.backend.model.standup_action_log import StandupActionLog
from src.backend.model.project import Project

def inspect_db():
    db = SessionStandup()
    try:
        project = db.query(Project).filter(Project.name == "recrude").first()
        if not project:
            print("Project 'recrude' not found.")
            return

        print(f"--- Blockers for 'recrude' ({project.id}) ---")
        blockers = db.query(Blocker).filter(Blocker.project_id == project.id).all()
        for b in blockers:
            print(f"ID: {b.id}, Reason: {b.reason}, ResolvedAt: {b.resolved_at}")

        print("\n--- Recent Action Logs for RESOLVED BLOCKER ---")
        logs = db.query(StandupActionLog).filter(StandupActionLog.action_taken.like("%RESOLVED BLOCKER%")).order_by(StandupActionLog.created_at.desc()).limit(10).all()
        for l in logs:
            print(f"ID: {l.id}, UpdateID: {l.update_id}, Action: {l.action_taken}, CreatedAt: {l.created_at}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_db()
