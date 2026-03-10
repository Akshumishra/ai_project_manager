from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.projects import Project
from app.schemas.projects import ProjectResponse
from app.models.users import User
from app.database import get_db
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import re

load_dotenv()

router = APIRouter()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN environment variable not set")

slack_client = WebClient(token=SLACK_BOT_TOKEN)

def normalize_channel_name(name: str) -> str:
    """Convert project name to Slack-safe channel name."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-]", "-", name)  
    name = re.sub(r"-+", "-", name)           
    return name[:21]                          

@router.post("/channels/{project_id}/create", response_model=ProjectResponse)
def create_channel(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.channel_id:
        raise HTTPException(status_code=400, detail="Slack channel already exists")

    channel_name = normalize_channel_name(project.project_name)
    try:
        response = slack_client.conversations_create(
            name=channel_name,
            is_private=False
        )
        channel_id = response["channel"]["id"]

    except SlackApiError as e:
        raise HTTPException(status_code=500, detail=f"Slack API error: {e.response['error']}")

    project.channel_id = channel_id
    db.commit()
    db.refresh(project)

    return project


@router.post("/channels/{project_id}/add-developer")
def add_developer_to_channel(project_id: str, developer_name: str, db: Session = Depends(get_db)):
    
    # Fetch project
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.channel_id:
        raise HTTPException(status_code=400, detail="Project channel not created yet")

    # Fetch developer
    developer = db.query(User).filter(User.name == developer_name).first()
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")

    slack_id = developer.slack_id
    channel_id = project.channel_id

    try:
        response = slack_client.conversations_invite(
            channel=channel_id,
            users=slack_id
        )

    except SlackApiError as e:
        error = e.response["error"]

        if error == "already_in_channel":
            return {"message": f"{developer_name} is already in the channel"}

        raise HTTPException(
            status_code=500,
            detail=f"Slack API error: {error}"
        )

    return {
        "message": f"{developer_name} successfully added to project channel",
        "channel_id": channel_id,
        "slack_id": slack_id
    }