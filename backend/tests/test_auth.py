from httpx import AsyncClient


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
