from functools import lru_cache
from pathlib import Path
from typing import Annotated

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "MLab"
    app_env: str = "development"
    app_secret_key: str = "development-secret-change-in-production"
    credential_encryption_key: str | None = None
    database_url: str = "sqlite+aiosqlite:///./data/mlab.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    default_ai_provider: str = "deepseek"
    default_ai_model: str = "deepseek-chat"
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.deepseek.com/v1"
    mock_ai_enabled: bool = False

    storage_backend: str = "local"
    local_storage_path: Path = Path("data/uploads")
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30
    max_upload_size_mb: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self
        if self.mock_ai_enabled:
            raise ValueError("MOCK_AI_ENABLED cannot be enabled in production")
        if len(self.app_secret_key) < 32 or self.app_secret_key.startswith("change-"):
            raise ValueError("APP_SECRET_KEY must be a random value of at least 32 characters")
        if not self.credential_encryption_key:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY is required in production")
        try:
            Fernet(self.credential_encryption_key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key") from exc
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
