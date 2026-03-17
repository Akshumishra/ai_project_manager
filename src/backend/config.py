import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM: str
    ALLOWED_ORIGINS: list
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    @field_validator("*", mode="before")
    @classmethod
    def clean_strings(cls, v, info):
        if isinstance(v, str):
            # Remove leading/trailing spaces and quotes
            return v.strip().strip('"').strip("'")
        return v

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
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../.env"),
        extra="ignore"
    )

settings = Settings()
