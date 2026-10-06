"""What happens to an application after a document is read or fails (US-00-004, US-00-005).

Compare the document's fields with the application, then recompute the application's status from
all of its current documents. A document that failed has nothing to compare, but it still holds the
application in review, so the status is recomputed for it too.
"""

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories.comparison import compare_document
from app.db.repositories.statuses import recompute_status

type Settle = Callable[[UUID], Awaitable[None]]

_APPLICATION_OF = text("SELECT application_id FROM documents WHERE id = :id")


def make_settle(factory: async_sessionmaker[AsyncSession], *, name_threshold: float) -> Settle:
    """The function the worker calls with a document id once the document is read or failed."""

    async def settle(document_id: UUID) -> None:
        await compare_document(factory, document_id, name_threshold=name_threshold)
        async with factory() as session:
            application_id = (
                await session.execute(_APPLICATION_OF, {"id": document_id})
            ).scalar_one_or_none()
        if application_id is not None:
            await recompute_status(factory, application_id)

    return settle
