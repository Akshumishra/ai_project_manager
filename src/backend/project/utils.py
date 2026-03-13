import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.backend.config import Config

logger = logging.getLogger(__name__)


async def send_invitation_email(to_email: str, project_name: str, inviter_name: str):
    """
    Main entry point for sending invitation emails.
    Tries SMTP (primary) then Resend (fallback).
    """
    subject = f"Invitation to collaborate on {project_name}"
    html_content = _get_invitation_html(to_email, project_name, inviter_name)

    result = _send_via_smtp(to_email, subject, html_content)
    return result


def _get_invitation_html(to_email: str, project_name: str, inviter_name: str) -> str:
    return f"""
    <div style="font-family: sans-serif; line-height: 1.5; color: #333;">
        <h2>Hello!</h2>
        <p><strong>{inviter_name}</strong> has invited you to collaborate on the project <strong>"{project_name}"</strong> in AI Project Manager.</p>
        <p>
            <a href="{Config.FRONTEND_URL}/register?email={to_email}" 
               style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 5px;">
               Get Started
            </a>
        </p>
        <p>If the button doesn't work, copy and paste this link: <br>
           {Config.FRONTEND_URL}/register?email={to_email}</p>
        <p>Please register using this email (<strong>{to_email}</strong>) to start collaborating!</p>
        <hr>
        <p style="font-size: 0.8em; color: #777;">Best,<br>The AI Project Manager Team</p>
    </div>
    """

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
