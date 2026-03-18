from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/ai_pm"
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: list = ["*"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_SECRET_KEY: str = "your_access_secret_key"
    REFRESH_SECRET_KEY: str = "your_refresh_secret_key"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email Config
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    BREVO_API_KEY: str | None = None
    SMTP_SERVER: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"
    OPENAI_API_KEY: str | None=None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_SIGNING_SECRET: str | None = None
    BOT_USER_ID: str | None = None
    SLACK_API_BASE_URL: str = "https://slack.com/api"
    APP_TITLE: str = "AI Project Manager API"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
Config = settings
