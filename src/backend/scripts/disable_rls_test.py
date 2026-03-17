import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def disable_rls_all():
    # Use OWNER credentials
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    print(f"Connecting as owner to disable RLS...")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        tables = ['tasks', 'standups', 'standup_updates', 'standup_action_logs', 'task_logs', 'projects', 'project_members']
        for table in tables:
            print(f"Disabling RLS on {table}...")
            conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        
        conn.commit()
        print("RLS disabled on all core tables.")

if __name__ == "__main__":
    disable_rls_all()
