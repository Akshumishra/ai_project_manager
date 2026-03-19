import os

base_dir = os.path.dirname(__file__)
json_path = os.path.join(base_dir, "current_db_data.json")
out_path = os.path.join(base_dir, "standalone_seed.py")

with open(json_path, "r") as f:
    data_str = f.read()

template = f"""import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.backend.db.database import get_session_local, Base
from sqlalchemy import insert
# Import all models to ensure they are registered with Base.metadata
from src.backend.model import user, user_detail, project, task, document, meeting, standup, standup_action_log, standup_update, requirement_chat, task_assigner_chat, task_log, tech_doc_chat, blocker

SEED_DATA = {data_str}

def load_db():
    session_factory = get_session_local()
    db = session_factory()
    
    print("Loading database from standalone seed...")
    try:
        # We iterate over tables in Base.metadata.sorted_tables to respect FK constraints
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            
            if table_name in SEED_DATA and len(SEED_DATA[table_name]) > 0:
                rows = SEED_DATA[table_name]
                print(f"Inserting {{len(rows)}} records into {{table_name}}...")
                
                try:
                    db.execute(insert(table).values(rows))
                except Exception as e:
                    if "UndefinedTable" in str(e) or "does not exist" in str(e):
                        print(f"Skipping table {{table_name}}: it does not exist in the database.")
                        db.rollback()
                    else:
                        print(f"Error inserting into {{table_name}}: {{e}}")
                        db.rollback()
            
        db.commit()
        print("Database load completed successfully!")
    except Exception as e:
        print(f"Critical error loading data: {{e}}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    load_db()
"""

with open(out_path, "w") as f:
    f.write(template)

print(f"Generated {out_path} successfully!")
