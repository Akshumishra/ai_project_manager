import sys
import os

# Add the project root to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from sqlalchemy import text
from src.backend.db.database import engine

# List of tables and their respective project identification logic
# Direct: has project_id column
# Indirect: needs join to identify project_id
RLS_CONFIG = {
    "projects": "id = current_setting('app.project_id')::uuid",
    "project_slack_details": "project_id = current_setting('app.project_id')::uuid",
    "project_members": "project_id = current_setting('app.project_id')::uuid",
    "tasks": "project_id = current_setting('app.project_id')::uuid",
    "documents": "project_id = current_setting('app.project_id')::uuid",
    "document_blocks": """
        doc_id IN (
            SELECT id FROM documents 
            WHERE project_id = current_setting('app.project_id')::uuid
        )
    """,
    "requirement_chats": "project_id = current_setting('app.project_id')::uuid",
}

def enable_rls():
    print("--- Starting RLS Migration ---")
    with engine.begin() as conn:
        for table, condition in RLS_CONFIG.items():
            print(f"Enabling RLS on table: {table}")
            
            # Enable RLS
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            
            # Force RLS (even for the table owner) - optional but safer for application users
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

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
