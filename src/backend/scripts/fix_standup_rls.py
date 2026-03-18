import sys
import os
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config

def fix_rls():
    # Use OWNER (postgres) to set policies
    # Extract owner URL by replacing app_user with postgres in the command or just reconstruct
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    print(f"Connecting as owner to update policies...")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        print("Granting base permissions to standup_user...")
        conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO standup_user"))
        conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO standup_user"))
        
        print("Adding RLS policies for standup_user...")
        
        # Policy for projects
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_projects') THEN
                    CREATE POLICY standup_user_select_projects ON projects FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))
        
        # Policy for tasks
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_tasks') THEN
                    CREATE POLICY standup_user_select_tasks ON tasks FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for project_members
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_members') THEN
                    CREATE POLICY standup_user_select_members ON project_members FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for users
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_users') THEN
                    CREATE POLICY standup_user_select_users ON users FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for slack details
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_slack') THEN
                    CREATE POLICY standup_user_select_slack ON project_slack_details FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for standups
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_standups') THEN
                    CREATE POLICY standup_user_select_standups ON standups FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for standup_updates
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_updates') THEN
                    CREATE POLICY standup_user_select_updates ON standup_updates FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for standup_action_logs
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_action_logs') THEN
                    CREATE POLICY standup_user_select_action_logs ON standup_action_logs FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Insert policy for tasks (allow standup_user to create new tasks)
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_insert_tasks') THEN
                    CREATE POLICY standup_user_insert_tasks ON tasks FOR INSERT TO standup_user WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Update policy for tasks (allow standup_user to update task status)
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_update_tasks') THEN
                    CREATE POLICY standup_user_update_tasks ON tasks FOR UPDATE TO standup_user USING (true) WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Insert policy for standup_updates
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_insert_updates') THEN
                    CREATE POLICY standup_user_insert_updates ON standup_updates FOR INSERT TO standup_user WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Insert policy for standup_action_logs
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_insert_action_logs') THEN
                    CREATE POLICY standup_user_insert_action_logs ON standup_action_logs FOR INSERT TO standup_user WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Insert policy for task_logs
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_insert_task_logs') THEN
                    CREATE POLICY standup_user_insert_task_logs ON task_logs FOR INSERT TO standup_user WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Policy for standups
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_insert_standups') THEN
                    CREATE POLICY standup_user_insert_standups ON standups FOR INSERT TO standup_user WITH CHECK (true);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_update_standups') THEN
                    CREATE POLICY standup_user_update_standups ON standups FOR UPDATE TO standup_user USING (true) WITH CHECK (true);
                END IF;
            END $$;
        """))

        # Policies for documents
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_all_documents') THEN
                    CREATE POLICY standup_user_all_documents ON documents FOR ALL TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policies for document_blocks
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_all_blocks') THEN
                    CREATE POLICY standup_user_all_blocks ON document_blocks FOR ALL TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Policy for task_logs SELECT (needed for INSERT RETURNING)
        conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'standup_user_select_task_logs') THEN
                    CREATE POLICY standup_user_select_task_logs ON task_logs FOR SELECT TO standup_user USING (true);
                END IF;
            END $$;
        """))

        # Refine Isolation Policies for core tables to only apply to app_user
        conn.execute(text("""
            -- Tasks
            DROP POLICY IF EXISTS project_isolation_tasks ON tasks;
            CREATE POLICY project_isolation_tasks ON tasks FOR ALL TO app_user 
            USING (project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid);
            
            -- Project Members
            DROP POLICY IF EXISTS project_isolation_members ON project_members;
            DROP POLICY IF EXISTS project_isolation_project_members ON project_members;
            CREATE POLICY project_isolation_members ON project_members FOR ALL TO app_user 
            USING (project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid);
            
            -- Users
            DROP POLICY IF EXISTS project_isolation_users ON users;
            CREATE POLICY project_isolation_users ON users FOR ALL TO app_user 
            USING (id IN (SELECT user_id FROM project_members WHERE project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid));

            -- Standups
            DROP POLICY IF EXISTS project_isolation_standups ON standups;
            CREATE POLICY project_isolation_standups ON standups FOR ALL TO app_user 
            USING (project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid);

            -- Standup Updates
            DROP POLICY IF EXISTS project_isolation_standup_updates ON standup_updates;
            CREATE POLICY project_isolation_standup_updates ON standup_updates FOR ALL TO app_user 
            USING (standup_id IN (SELECT id FROM standups WHERE project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid));

            -- Standup Action Logs
            DROP POLICY IF EXISTS project_isolation_standup_action_logs ON standup_action_logs;
            CREATE POLICY project_isolation_standup_action_logs ON standup_action_logs FOR ALL TO app_user 
            USING (update_id IN (SELECT id FROM standup_updates WHERE standup_id IN (SELECT id FROM standups WHERE project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid)));

            -- Documents
            DROP POLICY IF EXISTS project_isolation_documents ON documents;
            CREATE POLICY project_isolation_documents ON documents FOR ALL TO app_user 
            USING (project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid);
            
            -- Document Blocks
            DROP POLICY IF EXISTS project_isolation_document_blocks ON document_blocks;
            CREATE POLICY project_isolation_document_blocks ON document_blocks FOR ALL TO app_user 
            USING (doc_id IN (SELECT id FROM documents WHERE project_id = (NULLIF(current_setting('app.project_id'::text, true), ''::text))::uuid));
        """))

        conn.commit()
        print("RLS policies updated successfully.")

if __name__ == "__main__":
    fix_rls()
