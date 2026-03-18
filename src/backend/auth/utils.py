<<<<<<< feat/qa_chatbot
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
=======
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from src.backend.config import Config
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from src.backend.db.database import get_db
from src.backend.model.user import User
from uuid import UUID

bearer_scheme = HTTPBearer(auto_error=False)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def build_token_payload(user: User) -> dict:
    return {"user_id": str(user.id), "email": user.email}


def issue_token_pair(user: User) -> dict:
    token_data = build_token_payload(user)
    is_complete = user.detail is not None
    return {
        "access_token": create_access_token(data=token_data),
        "refresh_token": create_refresh_token(data=token_data),
        "token_type": "bearer",
        "name": user.name,
        "is_profile_complete": is_complete,
    }


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(Config.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.ACCESS_SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=int(Config.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.REFRESH_SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt


def verify_refresh_token(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, Config.REFRESH_SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        user_id = UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

    return user


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        jwt_token = token.credentials
        payload = jwt.decode(jwt_token, Config.ACCESS_SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        user_id = UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

>>>>>>> dev
    return user
