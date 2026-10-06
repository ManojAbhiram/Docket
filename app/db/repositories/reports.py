"""Dashboard counts and the verified export in Postgres (US-00-008, US-00-009).

Index decision (database rules): one count over `applications` and one ordered read of the verified
rows, at most a few thousand rows in one office, so no index yet; add one on `(status)` before the
table holds tens of thousands. The audit row is written in the transaction that reads the rows, so
an export cannot happen without its entry.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.export import VerifiedRow

_COUNTS = text(
    "SELECT count(*) FILTER (WHERE status = 'verified'), "
    "count(*) FILTER (WHERE status = 'needs_review'), "
    "count(*) FILTER (WHERE status = 'missing_documents'), "
    "count(*) FILTER (WHERE status = 'needs_review' AND rejected_at IS NOT NULL) "
    "FROM applications WHERE erased_at IS NULL"
)
_VERIFIED = text(
    "SELECT application_ref, full_name, date_of_birth, board, roll_number, category "
    "FROM applications WHERE status = 'verified' AND erased_at IS NULL "
    "ORDER BY application_ref"
)
_AUDIT = text("INSERT INTO export_audit (exported_by, row_count) VALUES (:user, :count)")


@dataclass(frozen=True)
class DashboardCounts:
    verified: int
    needs_review: int
    missing_documents: int
    rejected: int


class SqlReportStore:
    """The counts and the export, over the `applications` and `export_audit` tables."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def dashboard_counts(self) -> DashboardCounts:
        async with self._factory() as session:
            row = (await session.execute(_COUNTS)).one()
        return DashboardCounts(
            verified=row[0], needs_review=row[1], missing_documents=row[2], rejected=row[3]
        )

    async def export_verified(self, exported_by: UUID) -> list[VerifiedRow]:
        """Every verified application, and one audit row saying who took them and how many."""
        async with self._factory.begin() as session:
            rows = [
                VerifiedRow(
                    application_ref=r[0],
                    full_name=r[1],
                    date_of_birth=r[2],
                    board=r[3],
                    roll_number=r[4],
                    category=r[5],
                )
                for r in (await session.execute(_VERIFIED)).all()
            ]
            await session.execute(_AUDIT, {"user": exported_by, "count": len(rows)})
        return rows
