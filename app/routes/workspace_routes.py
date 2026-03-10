from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workspace import Workspace
from app.models.users import User
from app.services.email_service import send_invite_email
from slack_sdk.errors import SlackApiError
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
from dotenv import load_dotenv
import os

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

router = APIRouter()


@router.post("/invite")
def invite_to_workspace(email: str, workspace_id: str, db: Session = Depends(get_db)):
    
    # Fetch workspace from database
    workspace = db.query(Workspace).filter(
        Workspace.workspace_id == workspace_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    invite_link = workspace.invite_link

    # Send invite email
    email_sent = send_invite_email(email, invite_link)

    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send invite email"
        )

    return {
        "message": "Invite sent successfully",
        "email": email,
        "workspace_id": workspace_id,
        "invite_link": invite_link
    }


@router.post("/sync-slack-ids")
def sync_slack_ids(db: Session = Depends(get_db)):

    try:
        response = slack_client.users_list()
        members = response["members"]

    except SlackApiError as e:
        raise HTTPException(status_code=500, detail=e.response["error"])

    updated_users = []

    for member in members:

        # Skip bots and slackbot
        if member.get("is_bot") or member["id"] == "USLACKBOT":
            continue

        slack_id = member["id"]
        email = member.get("profile", {}).get("email")

        # Skip if email missing
        if not email:
            continue

        # Find user by email
        user = db.query(User).filter(User.email_id == email).first()

        if user:
            user.slack_id = slack_id
            updated_users.append(email)

    db.commit()

    return {
        "message": "Slack IDs updated successfully",
        "users_updated": updated_users
    }