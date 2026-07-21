import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from app.core.config import Settings


async def test_register_login_and_refresh(client: AsyncClient) -> None:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123", "display_name": "User"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["user"]["email"] == "user@example.com"
    assert body["access_token"]
    assert body["refresh_token"]

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123", "display_name": "User"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    login = await client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"}
    )
    assert login.status_code == 200
    refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
    )
    assert refresh.status_code == 200
    assert refresh.json()["refresh_token"] != login.json()["refresh_token"]


async def test_profile_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_provider_probe_requires_auth_and_blocks_private_urls(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "provider": "test",
        "base_url": "https://127.0.0.1/v1",
        "api_key": "test-key",
        "model": "test-model",
    }
    unauthenticated = await client.post("/api/v1/provider-credentials/test", json=payload)
    assert unauthenticated.status_code == 401

    private_url = await client.post(
        "/api/v1/provider-credentials/test", headers=auth_headers, json=payload
    )
    assert private_url.status_code == 422
    assert private_url.json()["error"]["code"] == "INVALID_PROVIDER_URL"

    providers = await client.get("/api/v1/providers", headers=auth_headers)
    assert providers.status_code == 200
    assert {item["id"] for item in providers.json()} >= {"openai", "deepseek", "qwen"}


def test_mock_provider_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="MOCK_AI_ENABLED"):
        Settings(
            app_env="production",
            app_secret_key="production-secret-with-more-than-32-characters",
            credential_encryption_key=Fernet.generate_key().decode(),
            mock_ai_enabled=True,
        )
