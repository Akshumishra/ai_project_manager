from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Email settings
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    BREVO_API_KEY: str | None = None
    SMTP_SERVER: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"
    OPENAI_API_KEY: str | None=None
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

