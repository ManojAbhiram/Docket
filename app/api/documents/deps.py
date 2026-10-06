"""What the document routes build per request."""

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.uploads import SqlUploadStore
from app.domain.uploads import Rasteriser


def get_upload_store(request: Request) -> SqlUploadStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return SqlUploadStore(factory)


def get_rasteriser(request: Request) -> Rasteriser:
    rasteriser: Rasteriser = request.app.state.rasteriser
    return rasteriser
