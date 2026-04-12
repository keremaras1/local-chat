"""Shared pytest fixtures.

Environment variables required by pydantic-settings are set here before any
app module is imported, so tests don't need a real .env file.
"""

import os

os.environ.setdefault("APP_SECRET", "test-secret-key-for-pytest-must-be-at-least-32-chars")
os.environ.setdefault("APP_PASSWORD", "testpassword")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app


class _MockResult:
    def scalars(self):
        return self

    def all(self):
        return []

    def scalar_one_or_none(self):
        return None


class _MockSession:
    async def execute(self, *args, **kwargs):
        return _MockResult()

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    def add(self, obj):
        pass


async def _mock_get_db():
    yield _MockSession()


@pytest.fixture
async def client():
    """HTTPX async client wired to the FastAPI app (no real network).

    The database dependency is overridden with a no-op mock so tests don't
    require a running Postgres instance.
    """
    app.dependency_overrides[get_db] = _mock_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
