import resend
import logging
from src.backend.config import Config

logger = logging.getLogger(__name__)


async def send_invitation_email(to_email: str, project_name: str, inviter_name: str):
    """
    Sends an invitation email using Resend.
    """
    if not Config.RESEND_API_KEY:
        logger.warning(
            f"RESEND_API_KEY not set. Skipping invitation email to {to_email}"
        )
        return

    resend.api_key = Config.RESEND_API_KEY

    subject = f"Invitation to collaborate on {project_name}"
    html_content = f"""
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

    try:
        r = resend.Emails.send(
            {
                "from": Config.EMAILS_FROM or "onboarding@resend.dev",
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }
        )
        logger.info(
            f"Invitation email sent via Resend to {to_email}. ID: {r.get('id')}"
        )
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via Resend: {str(e)}")
