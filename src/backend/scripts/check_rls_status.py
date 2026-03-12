import sys
import os

# Add the project root to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.backend.db.database import engine
from sqlalchemy import text

def check_rls():
    print("Checking RLS Policies in Database...")
    with engine.connect() as conn:
        # Check if RLS is enabled on tables
        rls_enabled = conn.execute(text("""
            SELECT relname, relrowsecurity 
            FROM pg_class c 
            JOIN pg_namespace n ON n.oid = c.relnamespace 
            WHERE n.nspname = 'public' AND relkind = 'r'
            AND relname IN ('projects', 'project_slack_details', 'project_members', 'tasks', 'documents', 'document_blocks', 'requirement_chats');
        """)).fetchall()
        
        print("\nTable RLS Status (relrowsecurity=True means enabled):")
        for table, enabled in rls_enabled:
            print(f" - {table}: {enabled}")

        # Check for specific policies
        policies = conn.execute(text("SELECT tablename, policyname FROM pg_policies;")).fetchall()
        print("\nActive Policies:")
        if not policies:
            print(" - None found")
        for tablename, policyname in policies:
            print(f" - {tablename}: {policyname}")

if __name__ == "__main__":
    try:
        check_rls()
    except Exception as e:
        print(f"Error checking RLS: {e}")
