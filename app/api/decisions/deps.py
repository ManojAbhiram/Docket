"""The store the decision routes build per request."""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repositories.decisions import SqlDecisionStore


def get_decision_store(request: Request) -> SqlDecisionStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    settings: Settings = request.app.state.settings
    return SqlDecisionStore(factory, name_threshold=settings.name_match_threshold)
