from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Literal

Role = Literal["admin", "manager", "engineer", "viewer"]

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    phone_number: str | None = None
    temp_password: str | None = None  # mock ได้
    # role removed - roles are assigned per project, not per user account

class UserUpdate(BaseModel):
    username: str
    email: EmailStr
    phone_number: str | None = None
    temp_password: str | None = None  # Optional - only update if provided

class UserInDB(BaseModel):
    username: str
    email: EmailStr
    password_hash: str
    role: Role = "viewer"
    created_at: datetime
    last_login_at: datetime | None = None

class UserPublic(BaseModel):
    username: str
    email: EmailStr
    role: Role
    created_at: datetime
    last_login_at: datetime | None = None

