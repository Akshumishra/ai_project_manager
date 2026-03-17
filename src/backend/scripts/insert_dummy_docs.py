import sys
import os
import uuid
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.backend.config import Config
from src.backend.db.database import SessionLocal
from src.backend.model.document import Document, DocumentBlock

def insert_dummy_docs():
    print("Connecting to DB to insert dummy docs...")
    # Use owner for full access
    owner_url = Config.DATABASE_URL.replace("app_user:test123", "postgres:password123")
    engine = create_engine(owner_url)
    
    with engine.connect() as conn:
        # 1. Project IDs
        ai_pm_id = 'df940dce-e506-4878-b500-c2dba9b15920'
        ai_tutor_id = 'b1389d5d-c3f9-481d-8749-492d9c559ed5'
        
        # 2. User IDs
        aarushi_id = '2b13d97c-4c32-405e-a3d9-7b7266af8c94'
        akshita_id = 'ca8980fb-7ecd-442c-84e8-caa0aa852d59'
        
        docs_to_insert = [
            {
                "project_id": ai_pm_id,
                "title": "Architecture Notes",
                "created_by": aarushi_id,
                "blocks": [
                    {"content": "The AI Project Manager uses a microservices architecture with FastAPI backends and Slack integrations.", "pos": "0"},
                    {"content": "Database: PostgreSQL with RLS enabled for project isolation.", "pos": "1"}
                ]
            },
            {
                "project_id": ai_pm_id,
                "title": "Product Roadmap",
                "created_by": akshita_id,
                "blocks": [
                    {"content": "Q1: Slack Integration & StandUp Agent.", "pos": "0"},
                    {"content": "Q2: Document Summarization & RAG implementation.", "pos": "1"}
                ]
            },
            {
                "project_id": ai_tutor_id,
                "title": "Learning Objectives",
                "created_by": aarushi_id,
                "blocks": [
                    {"content": "1. Provide personalized learning paths for students.", "pos": "0"},
                    {"content": "2. Real-time feedback on coding exercises.", "pos": "1"}
                ]
            }
        ]
        
        for d in docs_to_insert:
            print(f"Inserting document: {d['title']}")
            doc_id = uuid.uuid4()
            conn.execute(text("""
                INSERT INTO documents (id, project_id, title, created_by, created_at, updated_at)
                VALUES (:id, :project_id, :title, :created_by, now(), now())
            """), {"id": doc_id, "project_id": d["project_id"], "title": d["title"], "created_by": d["created_by"]})
            
            for b in d["blocks"]:
                conn.execute(text("""
                    INSERT INTO document_blocks (id, doc_id, content, position_key, type, last_edited_by, created_at, updated_at)
                    VALUES (:id, :doc_id, :content, :pos, 'paragraph', :editor, now(), now())
                """), {"id": uuid.uuid4(), "doc_id": doc_id, "content": b["content"], "pos": b["pos"], "editor": d["created_by"]})
        
        conn.commit()
        print("Dummy documentation inserted successfully.")

if __name__ == "__main__":
    insert_dummy_docs()
