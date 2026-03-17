from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException
import src.backend.model.user as user_model
from src.backend.db.database import SessionLocal
from src.backend.logger import get_logger
from . import schemas, utils

logger = get_logger("auth_service")

def register_user(request: schemas.UserCreate):
    session = SessionLocal()
    try:
        normalized_email = str(request.email).lower()
        existing_user = (
            session.query(user_model.User)
            .filter(func.lower(user_model.User.email) == normalized_email)
            .first()
        )

        if existing_user:
            if existing_user.deleted_at is not None:
                raise HTTPException(status_code=400, detail="Account was deleted. Please contact support.")
            if existing_user.password_hash is not None:
                raise HTTPException(status_code=409, detail="Email already registered")

            # Claiming an invited account
            existing_user.name = request.name
            existing_user.password_hash = utils.get_password_hash(request.password)
            session.commit()
            session.refresh(existing_user)
            return {
                "message": f"Account for {existing_user.name} activated successfully",
                "user_id": str(existing_user.id),
            }

        new_user = user_model.User(
            name=request.name,
            email=normalized_email,
            password_hash=utils.get_password_hash(request.password),
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return {
            "message": f"User {new_user.name} registered successfully",
            "user_id": str(new_user.id),
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="A database error occurred during registration. Please try again later."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during registration. Please contact support."
        )
    finally:
        session.close()


def login_user(request: schemas.UserLogin):
    session = SessionLocal()
    try:
        db_user = (
            session.query(user_model.User)
            .filter(
                func.lower(user_model.User.email) == str(request.email).lower(),
                user_model.User.deleted_at.is_(None)
            )
            .first()
        )

        if (
            not db_user
            or db_user.password_hash is None
            or not utils.verify_password(request.password, db_user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return utils.issue_token_pair(db_user)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="A database error occurred during login."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during login."
        )
    finally:
        session.close()


def refresh_token(request: schemas.TokenRefresh):
    session = SessionLocal()
    try:
        db_user = utils.verify_refresh_token(request.refresh_token, session)
        if db_user.deleted_at is not None:
             raise HTTPException(status_code=401, detail="User account deleted")
        return utils.issue_token_pair(db_user)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="A database error occurred during token refresh."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during token refresh."
        )
    finally:
        session.close()
