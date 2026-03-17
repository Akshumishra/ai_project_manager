import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from sqlalchemy import create_engine, text

def fix_user_id():
    # Use owner URL
    db_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        print("Mapping U0AJZR4M0DD to Aarushi...")
        # Get Aarushi's ID
        res = conn.execute(text("SELECT id FROM users WHERE name = 'Aarushi'")).fetchone()
        if not res:
            print("Aarushi not found.")
            return
        aarushi_id = res[0]
        
        # Update user_details
        conn.execute(text("UPDATE user_details SET slack_id = 'U0AJZR4M0DD' WHERE user_id = :uid"), {"uid": aarushi_id})
        
        # Update project_members
        conn.execute(text("UPDATE project_members SET slack_id = 'U0AJZR4M0DD' WHERE user_id = :uid"), {"uid": aarushi_id})
        
        # Clear orphan updates for the latest session so they can be re-processed
        conn.execute(text("DELETE FROM standup_updates WHERE standup_id = 'a37692e3-1fb5-4d6c-b27b-6cacbaa027c9'"))
        
        print("Fix applied successfully.")

if __name__ == "__main__":
    fix_user_id()
