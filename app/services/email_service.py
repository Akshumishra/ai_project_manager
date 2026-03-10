import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "aarushi@gkmit.co"
EMAIL_PASSWORD = "hnkhtwcfccdbgtlq"


def send_invite_email(receiver_email: str, invite_link: str):

    subject = "Workspace Invite"
    body = f"You have been invited to join the workspace.\n\nClick here to join:\n{invite_link}"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, receiver_email, msg.as_string())
        server.quit()

        return True

    except Exception as e:
        print("Email sending failed:", e)
        return False