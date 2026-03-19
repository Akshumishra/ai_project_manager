from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
import logging
from src.backend.db.database import get_db
from . import schemas, services, utils
import src.backend.model.user as user_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return services.register_user(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/login", response_model=schemas.Token)
def login_user(request: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        return services.login_user(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(request: schemas.TokenRefresh, db: Session = Depends(get_db)):
    try:
        return services.refresh_token(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/send-otp", response_model=schemas.MessageResponse)
def send_otp(request: schemas.OTPRequest, db: Session = Depends(get_db)):
    try:
        return services.send_otp(request, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post("/verify-otp", response_model=schemas.MessageResponse)
def verify_otp(request: schemas.OTPVerify):
    try:
        return services.verify_otp(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
