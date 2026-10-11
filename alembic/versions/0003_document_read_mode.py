"""document read mode and provenance

Revision: 0003
Revises: 0002
Created: 2026-10-11

Opt-in OpenRouter Vision (ADR-0015). Staff choose a reading mode per upload, so the document keeps
what was asked for (`requested_mode`), which engine actually read it (`read_engine`) and, when the
requested engine was not used, a safe reason code (`fallback_reason`). Existing rows are `free`.

Index decision: the Vision cap counts `gateway_calls` rows by engine over a rolling 24 hours, so
`idx_gateway_calls_engine_created_at` serves that one query. No `documents` filter is added: the
queue claim still reads `status = 'uploaded'` through the existing partial index.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the three provenance columns and the cap-count index."""
    op.execute(
        "ALTER TABLE documents "
        "ADD COLUMN IF NOT EXISTS requested_mode text NOT NULL DEFAULT 'free', "
        "ADD COLUMN IF NOT EXISTS read_engine text, "
        "ADD COLUMN IF NOT EXISTS fallback_reason text"
    )
    op.execute(
        "ALTER TABLE documents "
        "ADD CONSTRAINT chk_documents_requested_mode CHECK (requested_mode IN ('free', 'vision')), "
        "ADD CONSTRAINT chk_documents_provenance_lengths CHECK "
        "((read_engine IS NULL OR length(read_engine) <= 40) "
        "AND (fallback_reason IS NULL OR length(fallback_reason) <= 80))"
    )
    op.execute(
        "COMMENT ON COLUMN documents.requested_mode IS "
        "'What the uploader asked for: free (local OCR) or vision (OpenRouter).'"
    )
    op.execute(
        "COMMENT ON COLUMN documents.read_engine IS "
        "'The engine that read the document, null until it is read.'"
    )
    op.execute(
        "COMMENT ON COLUMN documents.fallback_reason IS "
        "'A short reason code when the requested engine was not used, never provider text.'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_gateway_calls_engine_created_at "
        "ON gateway_calls (engine, created_at)"
    )


def downgrade() -> None:
    """Remove what upgrade added."""
    op.execute("DROP INDEX IF EXISTS idx_gateway_calls_engine_created_at")
    op.execute(
        "ALTER TABLE documents DROP CONSTRAINT IF EXISTS chk_documents_provenance_lengths, "
        "DROP CONSTRAINT IF EXISTS chk_documents_requested_mode, "
        "DROP COLUMN IF EXISTS fallback_reason, DROP COLUMN IF EXISTS read_engine, "
        "DROP COLUMN IF EXISTS requested_mode"
    )
