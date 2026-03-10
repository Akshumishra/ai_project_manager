from pydantic import BaseModel, EmailStr
from uuid import UUID

class UserBase(BaseModel):
    name: str
    slack_id: str
    email_id: EmailStr

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: UUID

    class Config:
        orm_mode = True