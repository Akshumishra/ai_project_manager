import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.backend.config import settings
from .constants import INVITATION_EMAIL_SUBJECT, INVITATION_EMAIL_HTML_TEMPLATE

logger = logging.getLogger(__name__)


async def send_invitation_email(to_email: str, project_name: str, inviter_name: str):
    """
    Main entry point for sending invitation emails.
    Tries SMTP (primary) then Resend (fallback).
    """
    subject = INVITATION_EMAIL_SUBJECT.format(project_name=project_name)
    html_content = INVITATION_EMAIL_HTML_TEMPLATE.format(
        inviter_name=inviter_name,
        project_name=project_name,
        frontend_url=settings.FRONTEND_URL,
        to_email=to_email,
        slack_invite_url=settings.SLACK_INVITE_URL
    )

    result = _send_via_smtp(to_email, subject, html_content)
    return result


def _send_via_smtp(to_email: str, subject: str, html_content: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAILS_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent via SMTP to {to_email}")
        return {"status": "sent", "provider": "smtp"}
    except Exception as e:
        logger.error(f"SMTP failed: {e}")
        return None
