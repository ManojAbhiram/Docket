"""Write the comparison of a read document with its application (US-00-004). SQL lives here.

The result goes in `extracted_fields.match_result`. A field that does not match is flagged for
review with the reason `mismatch`, unless it already carries another reason (the table allows one):
then the earlier reason stays. A flag this step set earlier is cleared when the field now matches,
so running it again after a correction gives the rows a first run would. Every statement is bound
by the document id, and the document row is locked for the transaction so two runs cannot
interleave.
"""

import json
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.compare import (
    ApplicationValues,
    FieldToCompare,
    compare_fields,
    review_reason_after,
)

_LOAD_DOCUMENT = text(
    "SELECT coalesce(d.detected_type::text, 'unknown'), a.full_name, a.father_name, "
    "a.date_of_birth, a.board, a.roll_number, a.marks "
    "FROM documents d JOIN applications a ON a.id = d.application_id "
    "WHERE d.id = :document_id AND d.status = 'read' FOR UPDATE OF d"
)
_LOAD_FIELDS = text(
    "SELECT id, field_name::text, subject, value, review_reason FROM extracted_fields "
    "WHERE document_id = :document_id ORDER BY id"
)
_WRITE = text(
    "UPDATE extracted_fields SET match_result = CAST(:result AS match_result), "
    "needs_review = (CAST(:reason AS text) IS NOT NULL), review_reason = CAST(:reason AS text), "
    "updated_at = now() WHERE id = :field_id AND document_id = :document_id"
)


async def compare_document(
    factory: async_sessionmaker[AsyncSession], document_id: UUID, *, name_threshold: float
) -> None:
    """Compare every field of a read document with its application and store the results.

    A document that does not exist, or is not `read`, is left alone.
    """
    async with factory.begin() as session:
        loaded = (await session.execute(_LOAD_DOCUMENT, {"document_id": document_id})).first()
        if loaded is None:
            return
        document_type, full_name, father_name, born, board, roll, marks = loaded
        rows = (await session.execute(_LOAD_FIELDS, {"document_id": document_id})).all()
        results = compare_fields(
            document_type,
            [FieldToCompare(field_id=r[0], name=r[1], subject=r[2], value=r[3]) for r in rows],
            _application(full_name, father_name, born, board, roll, marks),
            name_threshold=name_threshold,
        )
        earlier = {r[0]: r[4] for r in rows}
        writes = [
            {
                "field_id": field_id,
                "document_id": document_id,
                "result": result,
                "reason": review_reason_after(result, earlier[field_id]),
            }
            for field_id, result in results
        ]
        if writes:
            await session.execute(_WRITE, writes)


def _application(
    full_name: str, father_name: str, born: date, board: str, roll: str, marks: object
) -> ApplicationValues:
    stored: object = json.loads(marks) if isinstance(marks, str) else marks
    if not isinstance(stored, dict):
        msg = "the application marks are not an object"
        raise TypeError(msg)
    return ApplicationValues(
        full_name=full_name,
        father_name=father_name,
        date_of_birth=born,
        board=board,
        roll_number=roll,
        marks={str(subject): int(mark) for subject, mark in stored.items()},
    )
