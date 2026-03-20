from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from src.backend.db.database import get_db
from src.backend.technical_doc.services.tech_doc_service import run_tech_doc_agent
from src.backend.utils.doc_utils import upsert_document
from src.backend.utils.workflow_utils import set_workflow_status
from src.backend.model.document import DocumentType
from src.backend.model.project import Project
from src.backend.technical_doc.constants import TechDocAgentConstants
from src.backend.slack.slack_service import setup_slack_channel_for_project
from src.backend.task_creator.task_creator_service import generate_and_save_tasks
from src.backend.utils.queue_utils import get_queue
from src.backend.config import settings
from .schemas import (
    TechDocAgentRequest,
    SaveTechDocRequest,
    TechDocResponseSchema,
    TechDocSaveResponseSchema,
)

router = APIRouter(prefix="/api/agent/projects", tags=["Technical Doc"])
AgentConst = TechDocAgentConstants


@router.get("/{project_id}/tech-doc-agent", response_model=TechDocResponseSchema)
async def start_tech_doc(project_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    """Initialize or resume the Tech Doc agent session."""
    return run_tech_doc_agent(db=db, user_id=user_id, project_id=project_id, is_start=True)


@router.post("/{project_id}/tech-doc-agent", response_model=TechDocResponseSchema)
async def run_tech_doc_turn(
    project_id: UUID,
    request: TechDocAgentRequest,
    db: Session = Depends(get_db),
):
    """Continue a chat session with the Tech Doc agent."""
    return run_tech_doc_agent(
        db=db,
        user_id=request.user_id,
        project_id=project_id,
        user_message=request.message,
        is_start=False,
    )


@router.post("/{project_id}/tech-doc", response_model=TechDocSaveResponseSchema)
async def save_tech_doc(
    project_id: UUID,
    request: SaveTechDocRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Finalize and save the technical document.
    Triggers task generation and Slack channel setup in the background.
    """
    # Save/update the document and mark the phase as completed
    result = upsert_document(
        db=db,
        project_id=project_id,
        user_id=request.user_id,
        document_type=DocumentType.TECHNICAL,
        markdown_content=request.document_markdown,
        title_label=AgentConst.TECH_DOC_LABEL,
    )
    set_workflow_status(db, project_id, AgentConst.WORKFLOW_NAME, "completed")
    db.commit()

    queue = get_queue()
    if settings.USE_REDIS and queue:
        queue.enqueue(
            generate_and_save_tasks, project_id, request.user_id,
            job_id=f"task-gen-{project_id}", job_timeout=600,
            result_ttl=86400, failure_ttl=86400,
        )
    else:
        background_tasks.add_task(generate_and_save_tasks, project_id, request.user_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if project and not project.slack_channel_id:
        background_tasks.add_task(setup_slack_channel_for_project, project_id, project.name)

    return {"status": "success", "message": result.get("message", "Document saved.")}
