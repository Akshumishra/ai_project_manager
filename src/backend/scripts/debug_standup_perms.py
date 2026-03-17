import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def debug_permissions():
    # Use STANDUP_DATABASE_URL (standup_user)
    print(f"Connecting with: {Config.STANDUP_DATABASE_URL}")
    engine = create_engine(Config.STANDUP_DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n--- Diagnostic: Standup User Visibility ---")
        
        # Check projects
        try:
            res = conn.execute(text("SELECT count(*) FROM projects")).fetchone()
            print(f"Projects count: {res[0]}")
        except Exception as e:
            print(f"Error reading projects: {e}")
            
        # Check tasks
        try:
            res = conn.execute(text("SELECT count(*) FROM tasks")).fetchone()
            print(f"Tasks count: {res[0]}")
        except Exception as e:
            print(f"Error reading tasks: {e}")

        # Check who am I
        res = conn.execute(text("SELECT current_user")).fetchone()
        print(f"Current User: {res[0]}")

if __name__ == "__main__":
    debug_permissions()
