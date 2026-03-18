"""
This script enables Row Level Security (RLS) on database tables to ensure strict data isolation between projects.
It implements policies that filter rows based on a session-level 'app.project_id' variable.
"""
import sys
import os

# Add the project root to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from sqlalchemy import text
from src.backend.db.database import get_session_local
from sqlalchemy import create_engine

# Allow overriding the engine for RLS migration (e.g., to run as superuser)
rls_db_url = os.getenv("DATABASE_URL_RLS")
if rls_db_url:
    migrate_engine = create_engine(rls_db_url)
else:
    factory = get_session_local()
    migrate_engine = factory.kw["bind"]
# Direct: has project_id column
# Indirect: needs join to identify project_id
RLS_CONFIG = {
    "projects": "id = NULLIF(current_setting('app.project_id', true), '')::uuid",
    "project_slack_details": "(NULLIF(current_setting('app.project_id', true), '') IS NULL) OR (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid)",
    "project_members": "project_id = NULLIF(current_setting('app.project_id', true), '')::uuid",
    "tasks": "project_id = NULLIF(current_setting('app.project_id', true), '')::uuid",
    "documents": "project_id = NULLIF(current_setting('app.project_id', true), '')::uuid",
    "document_blocks": """
        doc_id IN (
            SELECT id FROM documents 
            WHERE project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
        )
    """,
    "requirement_chats": "project_id = NULLIF(current_setting('app.project_id', true), '')::uuid",
    "users": """
        id IN (
            SELECT user_id FROM project_members 
            WHERE project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
        )
    """,
    "user_details": """
        user_id IN (
            SELECT user_id FROM project_members 
            WHERE project_id = NULLIF(current_setting('app.project_id', true), '')::uuid
        )
    """,
}

def enable_rls():
    print("--- Starting RLS Migration ---")
    with migrate_engine.begin() as conn:
        for table, condition in RLS_CONFIG.items():
            print(f"Enabling RLS on table: {table}")
            
            # Enable RLS
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            
            # Force RLS
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

            # Grant SELECT access to app_user
            conn.execute(text(f"GRANT SELECT ON TABLE {table} TO app_user;"))

            # Drop existing policy if it exists to make script idempotent
            conn.execute(text(f"DROP POLICY IF EXISTS project_isolation_{table} ON {table};"))

            # Create new policy
            policy_sql = f"""
            CREATE POLICY project_isolation_{table}
            ON {table}
            FOR ALL
            TO PUBLIC
            USING ({condition});
            """
            conn.execute(text(policy_sql))
            print(f"Successfully applied policy to {table}")

    print("--- RLS Migration Completed ---")

if __name__ == "__main__":
    try:
        enable_rls()
    except Exception as e:
        print(f"Migration failed: {e}")
