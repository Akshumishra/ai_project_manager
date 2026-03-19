import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def enable_rls_refined():
    # Use OWNER credentials
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    print(f"Connecting as owner to refine RLS...")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        # 1. Re-enable RLS on all core tables
        tables = ['tasks', 'standups', 'standup_updates', 'standup_action_logs', 'task_logs', 'projects', 'project_members']
        for table in tables:
            print(f"Enabling RLS on {table}...")
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

        # 2. Modify existing 'project_isolation' policies to ONLY apply to 'app_user'
        # This prevents them from interfering with 'standup_user'
        isolation_policies = {
            'tasks': 'project_isolation_tasks',
            'projects': 'project_isolation_projects',
            'project_members': 'project_isolation_members'
        }
        
        for table, policy in isolation_policies.items():
            print(f"Restricting {policy} to app_user...")
            # We recreate the policy restricted to 'app_user'
            # First drop if exists (already exists as per previous diagnostics)
            conn.execute(text(f"DROP POLICY IF EXISTS {policy} ON {table};"))
            
            # Recreate with TO app_user
            if table == 'projects':
                qual = "(id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid)"
            else:
                qual = "(project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid)"
                
            conn.execute(text(f"CREATE POLICY {policy} ON {table} FOR ALL TO app_user USING ({qual});"))

        conn.commit()
        print("RLS re-enabled and isolation policies refined.")

if __name__ == "__main__":
    enable_rls_refined()
