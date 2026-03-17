import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def reset_standup_data():
    # Use OWNER credentials for full deletion rights
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    print(f"Connecting to DB to reset test data...")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        # Tables to clear in order of dependencies
        tables = [
            'standup_action_logs',
            'standup_updates',
            'standups',
            'task_logs',
            'document_blocks',
            'documents'
        ]
        
        # Deleting content using TRUNCATE for speed and safety, or DELETE if preferred
        for table in tables:
            print(f"Clearing table: {table}")
            conn.execute(text(f"DELETE FROM {table};"))
        
        conn.commit()
        print("Data reset complete. Ready for clean end-to-end testing!")

if __name__ == "__main__":
    reset_standup_data()
