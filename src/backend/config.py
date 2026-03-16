from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Email Config
    EMAILS_FROM: str | None = None
    RESEND_API_KEY: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
