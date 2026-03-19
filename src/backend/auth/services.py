from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import random
import src.backend.model.user as user_model
from . import schemas, utils, email_utils
from src.backend.db.redis import redis_client


def register_user(request: schemas.UserCreate, db: Session):
    normalized_email = str(request.email).lower()
    
    # Check if email is verified in Redis
    verified_key = f"verified:{normalized_email}"
    if not redis_client.get(verified_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email not verified. Please verify your email first."
        )
    
    existing_user = (
        db.query(user_model.User)
        .filter(func.lower(user_model.User.email) == normalized_email)
        .first()
    )

    if existing_user:
        if existing_user.status == user_model.UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Email already registered"
            )
        if existing_user.status == user_model.UserStatus.DEACTIVATED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Account is deactivated, Please contact support"
            )

        # Claiming an invited account or updating an existing one
        existing_user.name = request.name
        existing_user.password_hash = utils.get_password_hash(request.password)
        existing_user.status = user_model.UserStatus.ACTIVE
        existing_user.is_verified = True
        db.commit()
        db.refresh(existing_user)
        return {
            "message": f"User {existing_user.name} registered successfully",
            "user_id": existing_user.id,
        }

    new_user = user_model.User(
        name=request.name,
        email=normalized_email,
        password_hash=utils.get_password_hash(request.password),
        status=user_model.UserStatus.ACTIVE,
        is_verified=True
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
    
    # Check if user already exists and is active
    existing_user = db.query(user_model.User).filter(func.lower(user_model.User.email) == email).first()
    if existing_user and existing_user.status == user_model.UserStatus.ACTIVE:
         raise HTTPException(
             status_code=status.HTTP_409_CONFLICT, 
             detail="Email already registered and active"
         )
    if existing_user and existing_user.status == user_model.UserStatus.DEACTIVATED:
         raise HTTPException(
             status_code=status.HTTP_409_CONFLICT, 
             detail="Account is deactivated, Please contact support"
         )

    # Rate limiting for resend (optional but good practice)
    resend_lock = redis_client.get(f"otp_lock:{email}")
    if resend_lock:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
            detail="Please wait before requesting a new code"
        )

    otp = str(random.randint(100000, 999999))
    
    # Store OTP in redis with expiry from constants
    redis_client.setex(f"otp:{email}", email_utils.constants.OTP_EXPIRY_SECONDS, otp)
    # Set resend lock
    redis_client.setex(f"otp_lock:{email}", email_utils.constants.OTP_RESEND_DELAY, "locked")
    
    if email_utils.send_otp_email(email, otp):
        return {"message": "Verification code sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to send verification email"
        )


def verify_otp(request: schemas.OTPVerify):
    email = request.email.lower()
    stored_otp = redis_client.get(f"otp:{email}")
    
    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Code expired or not requested. Please request a new one."
        )
        
    if stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid verification code"
        )
        
    # Mark as verified for 10 minutes in Redis
    redis_client.setex(f"verified:{email}", 600, "true")
    redis_client.delete(f"otp:{email}")
    redis_client.delete(f"otp_lock:{email}") # Clear resend lock on success
    
    return {"message": "Email verified successfully"}


def login_user(request: schemas.UserLogin, db: Session):
    db_user = (
        db.query(user_model.User)
        .filter(func.lower(user_model.User.email) == str(request.email).lower())
        .first()
    )

    if not db_user or db_user.status == user_model.UserStatus.DEACTIVATED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authentication failed or account deactivated"
        )

    if (
        db_user.password_hash is None
        or not utils.verify_password(request.password, db_user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )

    return utils.issue_token_pair(db_user)


def refresh_token(request: schemas.TokenRefresh, db: Session):
    db_user = utils.verify_refresh_token(request.refresh_token, db)
    return utils.issue_token_pair(db_user)
