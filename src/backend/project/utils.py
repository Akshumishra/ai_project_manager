import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.backend.config import Config

from . import constants

logger = logging.getLogger(__name__)


async def send_invitation_email(to_email: str, project_name: str, inviter_name: str):
    """
    Main entry point for sending invitation emails.
    Tries SMTP (primary) then Resend (fallback).
    """
    subject = constants.INVITATION_EMAIL_SUBJECT.format(project_name=project_name)
    html_content = constants.INVITATION_EMAIL_HTML_TEMPLATE.format(
        inviter_name=inviter_name,
        project_name=project_name,
        frontend_url=Config.FRONTEND_URL,
        to_email=to_email
    )

    result = _send_via_smtp(to_email, subject, html_content)
    return result


def _send_via_smtp(to_email: str, subject: str, html_content: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAILS_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent via SMTP to {to_email}")
        return {"status": "sent", "provider": "smtp"}
    except Exception as e:
        logger.error(f"SMTP failed: {e}")
        return None
