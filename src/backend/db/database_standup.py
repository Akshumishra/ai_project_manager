from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.config import Config

# This database engine uses the standup_user with restricted permissions
# Use a default SQLite database if STANDUP_DATABASE_URL is not set
standup_database_url = Config.STANDUP_DATABASE_URL or Config.DATABASE_URL or "sqlite:///./standup.db"
engine_standup = create_engine(standup_database_url)
SessionStandup = sessionmaker(autocommit=False, autoflush=False, bind=engine_standup)

def get_standup_db():
    db = SessionStandup()
    try:
        yield db
    finally:
        db.close()
