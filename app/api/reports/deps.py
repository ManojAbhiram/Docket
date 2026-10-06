"""The store the dashboard and export routes read from."""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.reports import SqlReportStore


def get_report_store(request: Request) -> SqlReportStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return SqlReportStore(factory)
