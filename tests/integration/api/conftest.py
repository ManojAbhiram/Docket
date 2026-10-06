"""A running app over the rolled-back test connection, with sign-in and a fake clock.

Every store the routes build from `app.state.session_factory` is overridden to use the test's
connection, so nothing a request writes outlives the test.
"""

from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.applications.deps import get_application_store, get_review_store
from app.api.auth.deps import get_auth_store
from app.api.documents.deps import get_upload_store
from app.core.config import Settings
from app.db.repositories.application_detail import SqlReviewStore
from app.db.repositories.applications import SqlApplicationStore
from app.db.repositories.auth import SqlAuthStore
from app.db.repositories.uploads import SqlUploadStore
from app.main import create_app
from tests.integration.helpers import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def api_settings() -> Settings:
    return Settings(
        _env_file=None,
        env="test",
        log_format="console",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5433/docket",
        session_cookie_secure=False,
        argon2_memory_kib=8,
        argon2_time_cost=1,
        import_max_bytes=4_000,
        upload_max_bytes=60_000,
    )


@pytest.fixture
async def api_app(
    api_settings: Settings, clock: FakeClock, factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    application = create_app(api_settings)
    application.dependency_overrides[get_auth_store] = lambda: SqlAuthStore(factory)
    application.dependency_overrides[get_application_store] = lambda: SqlApplicationStore(factory)
    application.dependency_overrides[get_review_store] = lambda: SqlReviewStore(factory)
    application.dependency_overrides[get_upload_store] = lambda: SqlUploadStore(factory)
    async with LifespanManager(application):
        application.state.clock = clock
        yield application


@pytest.fixture
async def api(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        yield client
