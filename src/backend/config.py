from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS").split(",")
