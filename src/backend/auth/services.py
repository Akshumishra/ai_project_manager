from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
import random
import src.backend.model.user as user_model
from . import schemas, utils, email_utils
from src.backend.db.redis import redis_client


def register_user(request: schemas.UserCreate, db: Session):
    normalized_email = str(request.email).lower()
    
    # Check if email is verified
    is_verified = redis_client.get(f"verified:{normalized_email}")
    if not is_verified:
        raise HTTPException(status_code=400, detail="Email not verified. Please verify OTP first.")
    
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

    # Clean up verification status
    redis_client.delete(f"verified:{normalized_email}")

    return {
        "message": f"User {new_user.name} registered successfully",
        "user_id": new_user.id,
    }


def send_otp(request: schemas.OTPRequest, db: Session):
    email = request.email.lower()
    
    # Check if user already exists
    existing_user = db.query(user_model.User).filter(func.lower(user_model.User.email) == email).first()
    if existing_user and existing_user.password_hash is not None:
         raise HTTPException(status_code=409, detail="Email already registered")

    otp = str(random.randint(100000, 999999))
    
    # Store OTP in redis with 10 min expiry
    redis_client.setex(f"otp:{email}", 600, otp)
    
    if email_utils.send_otp_email(email, otp):
        return {"message": "OTP sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")


def verify_otp(request: schemas.OTPVerify):
    email = request.email.lower()
    stored_otp = redis_client.get(f"otp:{email}")
    
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or not requested")
        
    if stored_otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    # Mark as verified for 30 minutes
    redis_client.setex(f"verified:{email}", 1800, "true")
    redis_client.delete(f"otp:{email}")
    
    return {"message": "Email verified successfully"}


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
