import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def debug_updates():
    # Use OWNER to see everything
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        print("\n--- Diagnostic: Standup Updates & Logs ---")
        
        # Check updates
        res = conn.execute(text("SELECT id, standup_id, user_id, reply_text, created_at FROM standup_updates ORDER BY created_at DESC LIMIT 5")).fetchall()
        print(f"Latest Updates ({len(res)}):")
        for row in res:
            print(row)
            
        # Check action logs
        res = conn.execute(text("SELECT update_id, action_taken, created_at FROM standup_action_logs ORDER BY created_at DESC LIMIT 5")).fetchall()
        print(f"\nLatest Action Logs ({len(res)}):")
        for row in res:
            print(row)

        # Check for any task logs
        res = conn.execute(text("SELECT task_id, log, created_at FROM task_logs ORDER BY created_at DESC LIMIT 5")).fetchall()
        print(f"\nLatest Task Logs ({len(res)}):")
        for row in res:
            print(row)

if __name__ == "__main__":
    debug_updates()
