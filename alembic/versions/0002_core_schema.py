"""core schema

Revision: 0002
Revises: 0001
Created: 2026-10-05

The first release of the schema in docs/design/schema.sql (12 tables, 8 enums, the append-only
guard on decisions). The SQL lives beside this file in 0002_core_schema.sql, a copy made when this
migration was written and never edited afterwards: a later change is a new migration.

Index decision: every index and its query shape is named in docs/design/data-model.md section 4.
No table is large yet, so nothing here runs concurrently or in batches.
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from app.db.sqlsplit import split_statements

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = Path(__file__).with_name("0002_core_schema.sql")
_TABLES = (
    "decisions, gateway_calls, extracted_fields, document_blobs, documents, applications, "
    "import_row_errors, imports, export_audit, idempotency_keys, sessions, users"
)
_TYPES = (
    "decision_action, call_outcome, match_result, field_name, document_status, document_type, "
    "application_status, user_role"
)


def upgrade() -> None:
    """Replace the probe table with the core schema."""
    op.drop_table("schema_probe")
    connection = op.get_bind()
    for statement in split_statements(_SCHEMA.read_text(encoding="utf-8")):
        connection.exec_driver_sql(statement)


def downgrade() -> None:
    """Drop the core schema and bring the probe table back."""
    connection = op.get_bind()
    connection.exec_driver_sql(f"DROP TABLE IF EXISTS {_TABLES} CASCADE")
    connection.exec_driver_sql("DROP FUNCTION IF EXISTS decisions_guard()")
    connection.exec_driver_sql("DROP FUNCTION IF EXISTS decisions_refuse_truncate()")
    connection.exec_driver_sql(f"DROP TYPE IF EXISTS {_TYPES}")
    op.create_table(
        "schema_probe",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schema_probe")),
    )
