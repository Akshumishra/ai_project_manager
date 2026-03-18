import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import text
from src.backend.db.database import engine

def setup_permissions():
    try:
        with engine.connect() as conn:
            # Wrap in transaction
            with conn.begin():
                print("Setting up standup_user...")
                
                # Check if user exists
                res = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname='standup_user'"))
                if not res.fetchone():
                    conn.execute(text("CREATE USER standup_user WITH PASSWORD 'standup123'"))
                    print("Created user standup_user")
                else:
                    conn.execute(text("ALTER USER standup_user WITH PASSWORD 'standup123'"))
                    print("Updated password for standup_user")

                # Database level permissions
                conn.execute(text("GRANT CONNECT ON DATABASE ai_manager_db TO standup_user"))
                conn.execute(text("GRANT USAGE ON SCHEMA public TO standup_user"))
                
                # Table level permissions
                # 1. Read access to everything
                conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO standup_user"))
                
                # 2. Complete list of tables for both users
                all_tables = [
                    "users", "user_details", "projects", "project_members",
                    "project_slack_details", "requirement_chats",
                    "tasks", "standups", "standup_updates", 
                    "standup_action_logs", "task_logs",
                    "documents", "document_blocks"
                ]
                
                # Grant access to standup_user (Limited)
                for table in all_tables:
                    conn.execute(text(f"GRANT INSERT, UPDATE, DELETE ON {table} TO standup_user"))
                    print(f"Granted INSERT, UPDATE, DELETE access on {table} to standup_user")
                
                # 3. Sequence access for auto-increment IDs
                conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO standup_user"))
                
                # 4. Setup app_user (The primary backend user)
                print("Setting up app_user grants...")
                for table in all_tables:
                    conn.execute(text(f"GRANT ALL PRIVILEGES ON {table} TO app_user"))
                    print(f"Granted ALL access on {table} to app_user")
                
                # Sequences for app_user too
                conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user"))
                
                print("Permissions setup complete!")

    except Exception as e:
        print(f"Error during permission setup: {e}")
        raise e

if __name__ == "__main__":
    setup_permissions()
