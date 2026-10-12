"""
Shared test fixtures.

Every API test runs against a fresh in-memory sqlite database. StaticPool keeps a
single connection alive for the whole test so the schema created at setup is still
there when the request handlers run.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Imported for the side effect of registering every table on Base.metadata.
# Aliased rather than `import app.models`, which would rebind the name `app` to
# the package and shadow the FastAPI instance imported above.
from app import models as _models  # noqa: F401


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
    }


@pytest_asyncio.fixture
async def db_session():
    """A session bound to a throwaway in-memory database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTP client wired to the app with the test database injected."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client, sample_user_data):
    """Client with a registered user's bearer token already attached."""
    response = await client.post("/api/auth/signup", json=sample_user_data)
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
