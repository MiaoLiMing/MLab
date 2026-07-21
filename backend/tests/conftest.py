import os
from collections.abc import AsyncIterator
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"
os.environ["APP_SECRET_KEY"] = "test-secret-with-enough-entropy-1234"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import rate_limiter
from app.db.base import Base
from app.db.session import SessionFactory, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def prepare_data_directory() -> None:
    Path("data").mkdir(exist_ok=True)


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    await rate_limiter.reset()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with SessionFactory() as db:
        await db.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "password123", "display_name": "测试用户"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
