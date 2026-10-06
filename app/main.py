"""Application factory for Docket.

Wiring only: settings, logging, tracing, middleware, exception handlers,
routers and the lifespan that owns the database engine. Run with
`uvicorn app.main:create_app --factory` locally; the image runs gunicorn
with uvicorn workers against the same factory.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import FastAPI

from app import __version__
from app.api.applications.router import router as applications_router
from app.api.auth.router import router as auth_router
from app.api.decisions.router import router as decisions_router
from app.api.documents.router import router as documents_router
from app.api.health.router import router as health_router
from app.api.imports.router import router as imports_router
from app.api.reports.router import router as reports_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.telemetry import configure_tracing
from app.db.repositories.documents import SqlDocumentStore
from app.db.repositories.gateway_calls import SqlCallLedger
from app.db.session import make_engine, make_session_factory
from app.domain.auth import LoginLimiter, Passwords
from app.domain.pdf import PopplerRasteriser
from app.gateway.reader import build_reader, engine_version
from app.jobs.runner import RunningWorker, start_worker
from app.jobs.settle import make_settle

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the engine on startup and dispose it on shutdown."""
    settings: Settings = app.state.settings
    engine = make_engine(settings)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    _start_sign_in(app, settings)
    app.state.rasteriser = PopplerRasteriser()
    app.state.worker = _start_document_worker(app, settings)
    log.info("startup", env=settings.env, version=__version__)
    try:
        yield
    finally:
        if app.state.worker is not None:
            await app.state.worker.stop()
        await engine.dispose()
        log.info("shutdown")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _start_document_worker(app: FastAPI, settings: Settings) -> RunningWorker | None:
    """Read uploaded documents inside this process when `WORKER_ENABLED` is set (ADR-0011)."""
    if not settings.worker_enabled:
        log.info("worker disabled; uploaded documents will wait")
        return None
    factory = app.state.session_factory
    ledger = SqlCallLedger(
        factory,
        asyncio.get_running_loop(),
        engine_version=engine_version(settings),
        preprocess=True,
    )
    return start_worker(
        SqlDocumentStore(factory),
        build_reader(settings, ledger),
        confidence_cutoff=settings.review_confidence_cutoff,
        idle_seconds=settings.worker_idle_seconds,
        sweep_interval_seconds=settings.sweep_interval_seconds,
        settle=make_settle(factory, name_threshold=settings.name_match_threshold),
    )


def _start_sign_in(app: FastAPI, settings: Settings) -> None:
    """What sign-in keeps in memory: the hasher, the limiter and a slot count for hashing.

    `app.state.clock` is read at call time, so a test can swap it for a fake one.
    """
    app.state.clock = _utc_now
    passwords = Passwords(
        memory_kib=settings.argon2_memory_kib,
        time_cost=settings.argon2_time_cost,
        parallelism=settings.argon2_parallelism,
    )
    app.state.passwords = passwords
    app.state.dummy_hash = passwords.hash("not a real password")
    app.state.hash_slots = asyncio.Semaphore(settings.login_hash_concurrency)
    app.state.login_limiter = LoginLimiter(
        max_failures=settings.login_max_failures,
        source_max_failures=settings.login_source_max_failures,
        window=timedelta(minutes=settings.login_window_minutes),
        lock=timedelta(minutes=settings.login_lock_minutes),
        clock=lambda: app.state.clock(),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application. Tests pass explicit settings."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)
    docs_enabled = settings.env != "production"
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(imports_router, prefix="/api")
    app.include_router(applications_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(decisions_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    configure_tracing(app, settings.app_name, __version__)
    return app
