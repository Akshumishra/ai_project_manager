from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from src.backend.model.project import ProjectWorkflowStatus

def get_workflow_status(db: Session, project_id: UUID, workflow_name: str) -> Optional[ProjectWorkflowStatus]:
    """Fetch workflow status for a project and workflow name."""
    return db.query(ProjectWorkflowStatus).filter(
        ProjectWorkflowStatus.project_id == project_id,
        ProjectWorkflowStatus.workflow_name == workflow_name
    ).first()

def is_status_stale(status: ProjectWorkflowStatus, seconds: int = 60) -> bool:
    """Check if a 'thinking' status is stale (older than specified seconds)."""
    if status.status != "thinking" or not status.updated_at:
        return False
    
    updated_at = status.updated_at.replace(tzinfo=timezone.utc) if status.updated_at.tzinfo is None else status.updated_at
        
    return datetime.now(timezone.utc) - updated_at > timedelta(seconds=seconds)

def set_workflow_status(
    db: Session,
    project_id: UUID,
    workflow_name: str,
    status_str: str,
    auto_commit: bool = True,
):
    """Update or create workflow status."""
    wf_status = get_workflow_status(db, project_id, workflow_name)
    if not wf_status:
        wf_status = ProjectWorkflowStatus(
            project_id=project_id,
            workflow_name=workflow_name,
            status=status_str
        )
        db.add(wf_status)
    else:
        wf_status.status = status_str
    
    if auto_commit:
        db.commit()
    else:
        db.flush()
    return wf_status

def check_completion_and_redirect(db: Session, project_id: UUID, workflow_name: str, redirect_path: str) -> Optional[Dict[str, Any]]:
    """Return redirect payload if workflow is complete."""
    wf_status = get_workflow_status(db, project_id, workflow_name)
    if wf_status and wf_status.status == "completed":
        return {
            "status": "completed",
            "saved": True,
            "redirect": redirect_path
        }
    return None

def handle_thinking_lock(db: Session, project_id: UUID, workflow_name: str) -> bool:
    """
    Check if locked. Returns True if logic should STOP (locked), 
    False if logic should PROCEED (not locked or stale).
    """
    wf_status = get_workflow_status(db, project_id, workflow_name)
    if wf_status and wf_status.status == "thinking":
        if not is_status_stale(wf_status):
            return True # Still locking
    return False
