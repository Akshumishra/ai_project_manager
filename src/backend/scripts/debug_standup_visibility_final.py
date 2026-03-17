import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.db.database_standup import SessionStandup
from src.backend.model.standup import Standup
from src.backend.model.project import ProjectMember
from sqlalchemy import text

def debug_standup_user():
    db = SessionStandup()
    sid = '1b5e53dc-ad4b-412c-ab0f-7eed3f2a3153'
    
    print(f"Current User: {db.execute(text('SELECT current_user')).scalar()}")
    
    s = db.query(Standup).get(sid)
    if s:
        print(f"Standup found: {s.id}, Project ID: {s.project_id}")
        
        # Try to find the member
        user_slack_id = "U0AL9DCL2L8"
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == s.project_id,
            ProjectMember.slack_id == user_slack_id
        ).first()
        
        if member:
            print(f"Member found: {member.id}, User ID: {member.user_id}")
        else:
            print(f"Member NOT found for slack_id {user_slack_id} and project {s.project_id}")
            # Check all members
            all_m = db.query(ProjectMember).filter(ProjectMember.project_id == s.project_id).all()
            print(f"Total members visible for this project: {len(all_m)}")
            for m in all_m:
                print(f" - Member: {m.id}, Slack ID: {m.slack_id}")
    else:
        print(f"Standup {sid} NOT found!")
    
    db.close()

if __name__ == "__main__":
    debug_standup_user()
