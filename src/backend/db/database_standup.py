from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.config import settings

# This database engine uses the standup_user with restricted permissions
# Use a default SQLite database if STANDUP_DATABASE_URL is not set
standup_database_url = settings.STANDUP_DATABASE_URL
engine_standup = create_engine(standup_database_url)
SessionStandup = sessionmaker(autocommit=False, autoflush=False, bind=engine_standup)

def get_standup_db():
    db = SessionStandup()
    try:
        yield db
    finally:
        db.close()
