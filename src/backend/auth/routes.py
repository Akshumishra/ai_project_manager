from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.backend.db.database import get_db
from . import schemas, services
import src.backend.model.user as user_model

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=list[schemas.UserRead])
def get_all_users(db: Session = Depends(get_db)):
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
