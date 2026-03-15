from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.technical_doc.services.tech_doc_gathering import (
    run_tech_doc_agent,
    save_final_tech_doc
)
from src.backend.technical_doc.schemas import TechDocAgentRequest, SaveTechDocRequest

router = APIRouter()

@router.get("/projects/{project_id}/tech-doc-agent")
def start_tech_doc_agent(project_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    response = run_tech_doc_agent(
        db=db,
        user_id=user_id,
        project_id=project_id,
        user_message=None,
        is_start=True
    )
    return response

@router.post("/projects/{project_id}/tech-doc-agent")
def run_agent(project_id: UUID, request: TechDocAgentRequest, db: Session = Depends(get_db)):
    response = run_tech_doc_agent(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        user_message=request.message,
        current_document_markdown=request.current_document_markdown,
        is_start=False
    )
    return response

@router.post("/projects/{project_id}/tech-doc")
def save_tech_doc(project_id: UUID, request: SaveTechDocRequest, db: Session = Depends(get_db)):
    response = save_final_tech_doc(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        document_markdown=request.document_markdown
    )
    return response
