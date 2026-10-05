"""The migrations produced the schema the design describes (docs/design/schema.sql)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

pytestmark = pytest.mark.integration

TABLES = {
    "applications",
    "decisions",
    "document_blobs",
    "documents",
    "export_audit",
    "extracted_fields",
    "gateway_calls",
    "idempotency_keys",
    "import_row_errors",
    "imports",
    "sessions",
    "users",
}


async def names(connection: AsyncConnection, query: str) -> set[str]:
    result = await connection.execute(text(query))
    return {str(row[0]) for row in result}


async def test_every_table_in_the_design_exists_and_the_probe_table_is_gone(
    connection: AsyncConnection,
) -> None:
    found = await names(
        connection,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
    )

    assert found >= TABLES
    assert "schema_probe" not in found


async def test_the_eight_enum_types_exist(connection: AsyncConnection) -> None:
    found = await names(
        connection,
        "SELECT typname FROM pg_type WHERE typtype = 'e' AND typnamespace = 'public'::regnamespace",
    )

    assert len(found) == 8


async def test_the_decision_log_guard_triggers_exist(connection: AsyncConnection) -> None:
    found = await names(
        connection,
        "SELECT tgname FROM pg_trigger WHERE tgrelid = 'decisions'::regclass AND NOT tgisinternal",
    )

    assert found == {"trg_decisions_append_only", "trg_decisions_no_truncate"}
