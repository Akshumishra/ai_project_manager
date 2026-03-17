import sys
import os
from sqlalchemy import create_engine, text

def check_app_user_grants():
    # Connect as postgres to check grants
    db_url = "postgresql://postgres:password123@localhost:5432/ai_manager_db"
    print(f"Connecting to DB to check app_user grants...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("\n--- Table Grants for app_user ---")
        res = conn.execute(text("""
            SELECT grantee, table_name, privilege_type 
            FROM information_schema.role_table_grants 
            WHERE grantee = 'app_user' AND table_name IN ('standups', 'standup_updates', 'standup_action_logs', 'tasks', 'project_members', 'users');
        """))
        for row in res:
            print(row)

if __name__ == "__main__":
    check_app_user_grants()
