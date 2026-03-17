import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.backend.config import settings

import logging
from . import constants

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, html_body: str):
    msg = MIMEMultipart()
    msg['From'] = settings.EMAILS_FROM
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_otp_email(to_email: str, otp_code: str):
    subject = constants.OTP_EMAIL_SUBJECT
    html_content = constants.OTP_EMAIL_HTML_TEMPLATE.format(otp_code=otp_code)
    return send_email(to_email, subject, html_content)
