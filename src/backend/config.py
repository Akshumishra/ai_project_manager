from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY", "secret")
    REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "refresh_secret")
    REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")

    # Email Config
    EMAILS_FROM = os.getenv("EMAILS_FROM", "onboarding@resend.dev")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    # CORS
    ALLOWED_ORIGINS = [
        origin.strip().strip('"').strip("'")
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
