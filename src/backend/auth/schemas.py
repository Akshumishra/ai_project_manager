from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

<<<<<<< feat/qa_chatbot
class TokenRefresh(BaseModel):
    refresh_token: str
=======
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    name: str
    is_profile_complete: bool = False


class TokenRefresh(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: EmailStr
    is_profile_complete: bool = False


class UserRegistrationResponse(BaseModel):
    message: str
    user_id: UUID


class UserDetailUpdate(BaseModel):
    skills: List[str]
    experience_years: str
    designation: str
>>>>>>> dev
