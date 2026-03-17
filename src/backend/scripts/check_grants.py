import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def check_grants():
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        print("\n--- Diagnostic: Table Grants for standup_user ---")
        res = conn.execute(text("""
            SELECT grantee, table_name, privilege_type 
            FROM information_schema.role_table_grants 
            WHERE grantee = 'standup_user'
            ORDER BY table_name
        """)).fetchall()
        for row in res:
            print(row)

        for table in ['tasks', 'standups', 'standup_updates', 'standup_action_logs', 'task_logs', 'documents', 'document_blocks', 'project_members', 'users']:
            print(f"\n--- Diagnostic: RLS Policies for {table} ---")
            res = conn.execute(text(f"""
                SELECT policyname, cmd, qual, with_check, polpermissive 
                FROM pg_policies 
                JOIN pg_policy ON pg_policy.polname = pg_policies.policyname
                WHERE tablename = '{table}'
            """)).fetchall()
            for row in res:
                print(row)

if __name__ == "__main__":
    check_grants()
