from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserResponse(ORMModel):
    id: UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    theme: str
    memory_enabled: bool
    default_assistant_id: UUID | None


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=500)
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    memory_enabled: bool | None = None
    default_assistant_id: UUID | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    user: UserResponse


class UsageSummary(BaseModel):
    conversations: int
    tasks: int
    documents: int
    input_tokens: int
    output_tokens: int
