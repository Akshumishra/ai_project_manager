from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.backend.db.database import get_db
from . import schemas, services, utils
import src.backend.model.user as user_model

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=list[schemas.UserRead])
def get_all_users(
    db: Session = Depends(get_db), user: user_model.User = Depends(utils.get_current_user)
):
    return db.query(user_model.User).all()


@router.post(
    "/register",
    response_model=schemas.UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    return services.register_user(request, db)


@router.post("/login", response_model=schemas.Token)
def login_user(request: schemas.UserLogin, db: Session = Depends(get_db)):
    return services.login_user(request, db)


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(request: schemas.TokenRefresh, db: Session = Depends(get_db)):
    return services.refresh_token(request, db)


@router.post("/send-otp")
def send_otp(request: schemas.OTPRequest, db: Session = Depends(get_db)):
    return services.send_otp(request, db)


@router.post("/verify-otp")
def verify_otp(request: schemas.OTPVerify):
    return services.verify_otp(request)
