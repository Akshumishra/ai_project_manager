from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.orm import Session

from src.backend.model.project import ProjectWorkflowStatus, WorkflowStatus


def get_workflow_status(db: Session, project_id: UUID, workflow_name: str) -> Optional[ProjectWorkflowStatus]:
    """Fetch workflow status entry for a project and workflow name."""
    return db.query(ProjectWorkflowStatus).filter(
        ProjectWorkflowStatus.project_id == project_id,
        ProjectWorkflowStatus.workflow_name == workflow_name
    ).first()

def is_status_stale(status_entry: ProjectWorkflowStatus, seconds: int = 60) -> bool:
    """Check if a 'thinking' status is stale (older than specified seconds)."""
    if status_entry.status != WorkflowStatus.THINKING or not status_entry.updated_at:
        return False
    
    updated_at = status_entry.updated_at.replace(tzinfo=timezone.utc) if status_entry.updated_at.tzinfo is None else status_entry.updated_at
    return datetime.now(timezone.utc) - updated_at > timedelta(seconds=seconds)

def set_workflow_status(
    db: Session,
    project_id: UUID,
    workflow_name: str,
    status: Union[WorkflowStatus, str],
    auto_commit: bool = True,
):
    """Update or create workflow status and commit to DB."""
    if isinstance(status, str):
        status = WorkflowStatus(status.lower())

    wf_status = get_workflow_status(db, project_id, workflow_name)
    if not wf_status:
        wf_status = ProjectWorkflowStatus(
            project_id=project_id,
            workflow_name=workflow_name,
            status=status
        )
        db.add(wf_status)
    else:
        wf_status.status = status
    
    if auto_commit:
        db.commit()
    else:
        db.flush()
    return wf_status

def check_agent_prerequisites(
    db: Session, 
    project_id: UUID, 
    workflow_name: str, 
    prereq_workflow: Optional[str] = None,
    redirect_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Consolidated check for prerequisites and completion status.
    Returns a redirect dictionary if logic should stop, else None.
    """
    current_status = get_workflow_status(db, project_id, workflow_name)
    if current_status and current_status.status == WorkflowStatus.COMPLETED:
        return {
            "status": "completed",
            "saved": True,
            "redirect": redirect_path or "/"
        }

    if prereq_workflow:
        pre_status = get_workflow_status(db, project_id, prereq_workflow)
        if not pre_status or pre_status.status != WorkflowStatus.COMPLETED:
            return {
                "status": "prerequisite_missing",
                "redirect": f"/{prereq_workflow.replace('_', '-')}",
                "message": f"Please complete the {prereq_workflow.replace('_', ' ').title()} phase first."
            }
            
    return None

def handle_agent_resumption(
    db: Session, 
    project_id: UUID, 
    workflow_name: str, 
    history: list,
    is_start: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Handles 'thinking' lock and resumption logic for agent start calls.
    Returns a 'resumed' response dictionary if logic should stop, else None.
    """
    if not is_start:
        return None

    wf_status = get_workflow_status(db, project_id, workflow_name)
    if not wf_status:
        return None

    is_interrupted = history and history[-1]["role"] == "user"
    if is_interrupted:
        if wf_status.status == WorkflowStatus.THINKING and not is_status_stale(wf_status):
            return {"messages": history, "status": "resumed", "thinking": True}
    
    if history and not is_interrupted:
        return {
            "status": "resumed",
            "messages": history
        }

    return None
