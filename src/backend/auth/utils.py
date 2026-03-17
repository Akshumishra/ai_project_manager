import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.backend.config import settings
import src.backend.model.user as user_model

def get_password_hash(password: str) -> str:
    """Simple SHA256 hashing for demonstration purposes."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify SHA256 hashed password."""
    return get_password_hash(plain_password) == hashed_password

def issue_token_pair(user: user_model.User) -> Dict[str, str]:
    # Placeholder for token generation logic
    # In a real app, you would use jwt.encode here
    return {
        "access_token": "fake_access_token",
        "refresh_token": "fake_refresh_token",
        "token_type": "bearer"
    }

def verify_refresh_token(token: str, db: Session) -> user_model.User:
    # Placeholder for token verification logic
    # In a real app, you would use jwt.decode and lookup the user
    user = db.query(user_model.User).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return user
