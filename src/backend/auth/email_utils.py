import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.backend.config import Config

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg['From'] = Config.EMAILS_FROM
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_otp_email(to_email: str, otp: str):
    subject = "Your Verification Code"
    body = f"Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
    return send_email(to_email, subject, body)
