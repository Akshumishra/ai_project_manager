import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.services.slack_service import SlackService
from src.backend.db.database import SessionLocal
from src.backend.model.standup import Standup

def inspect_latest_thread():
    db = SessionLocal()
    s = db.query(Standup).order_by(Standup.created_at.desc()).first()
    
    if not s:
        print("No standup found.")
        return

    print(f"--- Standup ID: {s.id} ---")
    print(f"Created At: {s.created_at}")
    print(f"Channel: {s.slack_channel_id}, TS: {s.message_ts}")
    
    slack = SlackService()
    try:
        replies = slack.list_replies(s.slack_channel_id, s.message_ts)
        print(f"Total Replies: {len(replies)}")
        for i, r in enumerate(replies):
            print(f"[{i}] User: {r.get('user')}, Text: {r.get('text')[:100]}...")
            print(f"    Full TS: {r.get('ts')}")
    except Exception as e:
        print(f"Error fetching replies: {e}")
    
    db.close()

if __name__ == "__main__":
    inspect_latest_thread()
