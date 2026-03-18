import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.backend.db.database import get_db
from src.backend.model.project import Project, ProjectMember
from src.backend.model.user import User
from src.backend.auth.utils import get_current_user
from src.backend.config import settings
from src.backend.slack.slack_service import lookup_user_by_email, invite_user_to_channel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/slack", tags=["Slack"])

class SlackJoinResponse(BaseModel):
    redirect_url: str
    invite_sent: bool

@router.post("/join/{project_id}", response_model=SlackJoinResponse)
async def join_slack_channel(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Join a Slack channel for the given project.
    Looks up the user by their email. If found, invites them to the channel and 
    saves their slack ID. Otherwise, just redirects to Slack app.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    channel_id = None
    
    # Try fetching channel_id from ProjectSlackDetail or Project model
    if project.slack_channel_id:
        channel_id = project.slack_channel_id
    else:
        # Check ProjectSlackDetail just in case
        from src.backend.model.project import ProjectSlackDetail
        detail = db.query(ProjectSlackDetail).filter(ProjectSlackDetail.project_id == project_id).first()
        if detail and detail.channel_id:
            channel_id = detail.channel_id

    if not channel_id:
        raise HTTPException(status_code=400, detail="Slack channel has not been created for this project yet")

    workspace_domain = settings.SLACK_WORKSPACE_NAME

    # Fallback web URL
    redirect_url_web = f"https://{workspace_domain}.slack.com/app_redirect?channel={channel_id}"

    invite_sent = False

    # Lookup user by email
    slack_user = lookup_user_by_email(current_user.email)
    
    if slack_user:
        slack_user_id = slack_user.get("id")
        if slack_user_id:
            # Save to ProjectMember
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            
            if member:
                member.slack_id = slack_user_id
                db.commit()
            
            # Invite to channel
            try:
                invite_res = invite_user_to_channel(channel_id, slack_user_id)
                if invite_res.get("ok"):
                    invite_sent = True
            except Exception as e:
                logger.error(f"Failed to invite {current_user.email} to channel {channel_id}: {e}")
                pass
    
    return {
        "redirect_url": redirect_url_web,
        "invite_sent": invite_sent
    }
