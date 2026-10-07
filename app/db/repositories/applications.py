"""Applications and their imports in Postgres (US-00-001). SQL for both lives here and nowhere else.

An import runs in one transaction behind a transaction-scoped advisory lock, so two imports of the
same file cannot both pass the "already in the database" check; `uq_applications_application_ref`
is the backstop. List index decision (database rules): `ORDER BY updated_at DESC, id DESC` over at
most a few thousand rows in one office needs no index yet; add one on `(updated_at, id)` before the
table holds tens of thousands.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.flag import FlaggedField, flag_reason
from app.domain.importing import ImportOutcome, SavedImport
from app.domain.paging import decode_cursor, encode_cursor

_IMPORT_LOCK = 7001
_LOCK = text("SELECT pg_advisory_xact_lock(:key)")
_EXISTING = text(
    "SELECT application_ref FROM applications WHERE application_ref = ANY(CAST(:refs AS text[]))"
)
_INSERT_IMPORT = text(
    "INSERT INTO imports (uploaded_by, source_name, rows_read, rows_created, rows_rejected) "
    "VALUES (:uploaded_by, :source_name, :rows_read, :rows_created, :rows_rejected) RETURNING id"
)
_INSERT_APPLICATION = text(
    "INSERT INTO applications (import_id, application_ref, full_name, father_name, date_of_birth, "
    "board, roll_number, marks, category) VALUES (:import_id, :application_ref, :full_name, "
    ":father_name, :date_of_birth, :board, :roll_number, CAST(:marks AS jsonb), :category)"
)
_INSERT_ERROR = text(
    "INSERT INTO import_row_errors (import_id, row_number, column_name, reason_code) "
    "VALUES (:import_id, :row_number, :column_name, :reason_code)"
)
_LIST = text(
    "SELECT id, application_ref, full_name, father_name, date_of_birth, board, roll_number, marks, "
    "category, status::text, rejected_at IS NOT NULL, created_at, updated_at FROM applications "
    "WHERE erased_at IS NULL "
    "AND (CAST(:status AS application_status) IS NULL "
    "OR status = CAST(:status AS application_status)) "
    "AND (CAST(:rejected AS boolean) IS NULL "
    "OR (rejected_at IS NOT NULL) = CAST(:rejected AS boolean)) "
    "AND (CAST(:cursor_at AS timestamptz) IS NULL "
    "OR (updated_at, id) < (CAST(:cursor_at AS timestamptz), CAST(:cursor_id AS uuid))) "
    "ORDER BY updated_at DESC, id DESC LIMIT :fetch"
)
# The queue reason (ISSUE-004). Index decision: both reads filter by `application_id` through
# `documents`, whose `idx_documents_application_id` exists, and touch only a page of ids (at most
# the page limit), so no new index.
_FLAGGED_FIELDS = text(
    "SELECT d.application_id, f.field_name::text, f.subject, f.review_reason "
    "FROM extracted_fields f JOIN documents d ON d.id = f.document_id "
    "WHERE d.application_id = ANY(CAST(:ids AS uuid[])) AND f.needs_review"
)
_FAILED_DOCUMENTS = text(
    "SELECT application_id, count(*) FROM documents "
    "WHERE application_id = ANY(CAST(:ids AS uuid[])) AND status = 'failed' "
    "GROUP BY application_id"
)


@dataclass(frozen=True)
class ApplicationRecord:
    id: UUID
    application_ref: str
    full_name: str
    father_name: str
    date_of_birth: date
    board: str
    roll_number: str
    marks: dict[str, int]
    category: str
    status: str
    rejected: bool
    created_at: datetime
    updated_at: datetime
    flag_reason: str | None = None


@dataclass(frozen=True)
class ApplicationPage:
    data: tuple[ApplicationRecord, ...]
    next_cursor: str | None


class SqlApplicationStore:
    """The `applications`, `imports` and `import_row_errors` tables."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def run_import(
        self,
        uploaded_by: UUID,
        source_name: str,
        parse: Callable[[frozenset[str]], ImportOutcome],
    ) -> SavedImport:
        """Parse the file against what is already stored, then save the good rows and the errors.

        `parse` is called with the application ids already in the database, so a row that repeats
        one is refused with its row number like any other bad row.
        """
        async with self._factory.begin() as session:
            await session.execute(_LOCK, {"key": _IMPORT_LOCK})
            outcome = parse(frozenset())
            refs = [row.application_ref for row in outcome.rows]
            found = (await session.execute(_EXISTING, {"refs": refs})).scalars().all()
            if found:
                outcome = parse(frozenset(found))
            import_id = await self._save(session, uploaded_by, source_name, outcome)
        return SavedImport(
            id=import_id,
            rows_read=outcome.rows_read,
            rows_created=len(outcome.rows),
            errors=outcome.errors,
        )

    async def _save(
        self, session: AsyncSession, uploaded_by: UUID, source_name: str, outcome: ImportOutcome
    ) -> UUID:
        import_id: UUID = (
            await session.execute(
                _INSERT_IMPORT,
                {
                    "uploaded_by": uploaded_by,
                    "source_name": source_name,
                    "rows_read": outcome.rows_read,
                    "rows_created": len(outcome.rows),
                    "rows_rejected": len(outcome.errors),
                },
            )
        ).scalar_one()
        if outcome.rows:
            await session.execute(
                _INSERT_APPLICATION,
                [
                    {
                        "import_id": import_id,
                        "application_ref": row.application_ref,
                        "full_name": row.full_name,
                        "father_name": row.father_name,
                        "date_of_birth": row.date_of_birth,
                        "board": row.board,
                        "roll_number": row.roll_number,
                        "marks": json.dumps(row.marks),
                        "category": row.category,
                    }
                    for row in outcome.rows
                ],
            )
        if outcome.errors:
            await session.execute(
                _INSERT_ERROR,
                [
                    {
                        "import_id": import_id,
                        "row_number": error.row_number,
                        "column_name": error.column_name,
                        "reason_code": error.reason_code,
                    }
                    for error in outcome.errors
                ],
            )
        return import_id

    async def list_page(
        self, *, limit: int, cursor: str | None, status: str | None, rejected: bool | None
    ) -> ApplicationPage:
        """One page, newest change first. Asks for one extra row to know if there is a next page."""
        cursor_at, cursor_id = decode_cursor(cursor) if cursor else (None, None)
        async with self._factory() as session:
            rows = (
                await session.execute(
                    _LIST,
                    {
                        "status": status,
                        "rejected": rejected,
                        "cursor_at": cursor_at,
                        "cursor_id": str(cursor_id) if cursor_id else None,
                        "fetch": limit + 1,
                    },
                )
            ).all()
        records = tuple(
            ApplicationRecord(
                id=r[0],
                application_ref=r[1],
                full_name=r[2],
                father_name=r[3],
                date_of_birth=r[4],
                board=r[5],
                roll_number=r[6],
                marks=r[7],
                category=r[8],
                status=r[9],
                rejected=r[10],
                created_at=r[11],
                updated_at=r[12],
            )
            for r in rows
        )
        page = await self._with_flag_reasons(records[:limit])
        more = len(records) > limit
        return ApplicationPage(
            data=page,
            next_cursor=encode_cursor(page[-1].updated_at, page[-1].id) if more else None,
        )

    async def _with_flag_reasons(
        self, records: tuple[ApplicationRecord, ...]
    ) -> tuple[ApplicationRecord, ...]:
        """Add the queue reason to each application that needs review. Two reads for the page."""
        ids = [r.id for r in records if r.status == "needs_review"]
        if not ids:
            return records
        async with self._factory() as session:
            field_rows = (await session.execute(_FLAGGED_FIELDS, {"ids": ids})).all()
            failed_rows = (await session.execute(_FAILED_DOCUMENTS, {"ids": ids})).all()
        fields: dict[UUID, list[FlaggedField]] = {}
        for row in field_rows:
            fields.setdefault(row[0], []).append(FlaggedField(row[1], row[2], row[3]))
        failed = {row[0]: row[1] for row in failed_rows}
        return tuple(
            replace(
                r,
                flag_reason=flag_reason(fields.get(r.id, []), failed_documents=failed.get(r.id, 0)),
            )
            if r.id in ids
            else r
            for r in records
        )
