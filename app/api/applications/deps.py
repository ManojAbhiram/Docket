"""The store the application and import routes read from."""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.application_detail import SqlReviewStore
from app.db.repositories.applications import SqlApplicationStore


def get_application_store(request: Request) -> SqlApplicationStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return SqlApplicationStore(factory)


def get_review_store(request: Request) -> SqlReviewStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return SqlReviewStore(factory)
