import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use SQLite in-memory for tests
os.environ.setdefault("PHI_ENCRYPTION_KEY", "gX2kP7nQwRtUvYzAbCdEfGhIjKlMnOpQ=")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-long!!")
os.environ.setdefault("IP_HASH_SALT", "test-ip-hash-salt-32-chars-long!!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PRIMARY_LLM_MODEL", "gpt-4o")
os.environ.setdefault("VERIFIER_LLM_PROVIDER", "anthropic")
os.environ.setdefault("VERIFIER_LLM_MODEL", "claude-sonnet-4-6")
os.environ.setdefault("VERIFIER_LLM_API_KEY", "test-key")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
