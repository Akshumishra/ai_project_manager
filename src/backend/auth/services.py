from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
import src.backend.model.user as user_model
from . import schemas, utils


def register_user(request: schemas.UserCreate, db: Session):
    normalized_email = str(request.email).lower()
    existing_user = (
        db.query(user_model.User)
        .filter(func.lower(user_model.User.email) == normalized_email)
        .first()
    )

    if existing_user:
        if existing_user.password_hash is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        # Claiming an invited account
        existing_user.name = request.name
        existing_user.password_hash = utils.get_password_hash(request.password)
        db.commit()
        db.refresh(existing_user)
        return {
            "message": f"Account for {existing_user.name} activated successfully",
            "user_id": existing_user.id,
        }

    new_user = user_model.User(
        name=request.name,
        email=normalized_email,
        password_hash=utils.get_password_hash(request.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": f"User {new_user.name} registered successfully",
        "user_id": new_user.id,
    }


def login_user(request: schemas.UserLogin, db: Session):
    db_user = (
        db.query(user_model.User)
        .filter(func.lower(user_model.User.email) == str(request.email).lower())
        .first()
    )

    if (
        not db_user
        or db_user.password_hash is None
        or not utils.verify_password(request.password, db_user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return utils.issue_token_pair(db_user)


def refresh_token(request: schemas.TokenRefresh, db: Session):
    db_user = utils.verify_refresh_token(request.refresh_token, db)
    return utils.issue_token_pair(db_user)
