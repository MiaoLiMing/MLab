from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ORMModel


class ProviderInfo(BaseModel):
    id: str
    name: str
    base_url: str
    example_models: list[str]


class CredentialCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=80)
    base_url: HttpUrl
    api_key: str = Field(min_length=4, max_length=500)


class CredentialResponse(ORMModel):
    id: UUID
    provider: str
    display_name: str
    base_url: str
    key_hint: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CredentialTestRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    base_url: HttpUrl
    api_key: str = Field(min_length=4, max_length=500)
    model: str | None = Field(default=None, max_length=120)


class CredentialTestResponse(BaseModel):
    ok: bool
    latency_ms: int
    models: list[str] = Field(default_factory=list)
    message: str


class ModelConfigCreate(BaseModel):
    credential_id: UUID | None = None
    provider: str = Field(min_length=1, max_length=50)
    model_id: str = Field(min_length=1, max_length=120)
    alias: str = Field(min_length=1, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ModelConfigUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=1, max_length=120)
    parameters: dict[str, Any] | None = None
    is_default: bool | None = None


class ModelConfigResponse(ORMModel):
    id: UUID
    credential_id: UUID | None
    provider: str
    model_id: str
    alias: str
    parameters: dict[str, Any]
    is_default: bool
    created_at: datetime
    updated_at: datetime
