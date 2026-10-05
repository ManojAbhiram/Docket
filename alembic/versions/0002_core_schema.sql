-- Docket: database schema (PostgreSQL 16)
-- Written by data-model beside docs/design/data-model.md, which gives the
-- reason for every table, column, index and constraint below.
--
-- Applies in one transaction to an empty database: enum types first, then
-- tables in foreign-key order, each followed by its comments and indexes.
-- It becomes alembic migration 0002 (0001 is the schema_probe table, which
-- 0002 drops). Paste it into the migration as one op.execute per statement
-- without the BEGIN and COMMIT lines (alembic owns the transaction and the
-- asyncpg driver runs one statement at a time), and write the Down that drops
-- everything in reverse. Every change after the first release is its own
-- migration (db-migration), never an edit to this file.

BEGIN;

CREATE TYPE user_role AS ENUM ('staff', 'verifier');
CREATE TYPE application_status AS ENUM ('verified', 'needs_review', 'missing_documents');
CREATE TYPE document_type AS ENUM ('10th_marksheet', '12th_marksheet', 'id_proof', 'transfer_certificate', 'unknown');
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'read', 'failed');
CREATE TYPE field_name AS ENUM ('name', 'father_name', 'dob', 'board', 'roll_number', 'marks', 'document_number');
CREATE TYPE match_result AS ENUM ('match', 'mismatch', 'skipped');
CREATE TYPE call_outcome AS ENUM ('pending', 'ok', 'error', 'refused');
CREATE TYPE decision_action AS ENUM ('approve', 'correct', 'reject');

-- users: the admissions staff and verifiers who sign in.
-- Serves US-00-011
CREATE TABLE users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    username text NOT NULL,
    display_name text NOT NULL,
    role user_role NOT NULL,
    password_hash text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    session_version integer NOT NULL DEFAULT 1,
    last_login_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT chk_users_username_not_blank CHECK (btrim(username) <> ''),
    CONSTRAINT chk_users_session_version_positive CHECK (session_version >= 1),
    CONSTRAINT chk_users_text_lengths CHECK (length(username) <= 64 AND length(display_name) <= 120)
);
COMMENT ON TABLE users IS 'A staff member or verifier. Seeded accounts only, never deleted, only deactivated. Serves US-00-011.';
COMMENT ON COLUMN users.id IS 'Surrogate key referenced by every audit column.';
COMMENT ON COLUMN users.username IS 'Sign-in name, unique ignoring case. [personal data]';
COMMENT ON COLUMN users.display_name IS 'Name shown in the decision log. [personal data]';
COMMENT ON COLUMN users.role IS 'staff or verifier, the only two roles in the product.';
COMMENT ON COLUMN users.password_hash IS 'Argon2id hash of the password, never the password.';
COMMENT ON COLUMN users.is_active IS 'False blocks sign-in and revokes sessions without deleting audit history.';
COMMENT ON COLUMN users.session_version IS 'Incremented to end every session of this user at once.';
COMMENT ON COLUMN users.last_login_at IS 'Last successful sign-in.';
COMMENT ON COLUMN users.created_at IS 'When the account was seeded.';
COMMENT ON COLUMN users.updated_at IS 'Last change to this row.';
-- Sign-in looks the user up by name, ignoring case.
CREATE UNIQUE INDEX uq_users_username ON users (lower(username));

-- sessions: a signed-in browser, found by the hash of its cookie token.
-- Serves US-00-011
CREATE TABLE sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash bytea NOT NULL,
    session_version integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CONSTRAINT sessions_pkey PRIMARY KEY (id),
    CONSTRAINT chk_sessions_expiry_after_creation CHECK (expires_at > created_at)
);
COMMENT ON TABLE sessions IS 'One signed-in browser. A request is valid only if the row is live and session_version matches the user. Serves US-00-011.';
COMMENT ON COLUMN sessions.id IS 'Surrogate key.';
COMMENT ON COLUMN sessions.user_id IS 'The user this session belongs to.';
COMMENT ON COLUMN sessions.token_hash IS 'SHA-256 of the random cookie token, so a database leak yields no usable cookie.';
COMMENT ON COLUMN sessions.session_version IS 'The user session_version when the session was created.';
COMMENT ON COLUMN sessions.created_at IS 'When the user signed in.';
COMMENT ON COLUMN sessions.last_seen_at IS 'Last authenticated request, for the idle timeout.';
COMMENT ON COLUMN sessions.expires_at IS 'Absolute end of the session.';
COMMENT ON COLUMN sessions.revoked_at IS 'Set on sign-out, null while the session is usable.';
-- Every request resolves the cookie to a session by token hash.
CREATE UNIQUE INDEX uq_sessions_token_hash ON sessions (token_hash);
-- Foreign-key index: end all sessions of one user.
CREATE INDEX idx_sessions_user_id ON sessions (user_id);

-- idempotency_keys: the first result of a creating request, replayed on a retry.
-- Serves US-00-001, US-00-002, US-00-007
CREATE TABLE idempotency_keys (
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key uuid NOT NULL,
    operation text NOT NULL,
    request_hash bytea NOT NULL,
    response_status smallint,
    resource_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT idempotency_keys_pkey PRIMARY KEY (user_id, key),
    CONSTRAINT chk_idempotency_keys_operation CHECK (operation IN ('create_import', 'upload_document', 'create_decision')),
    CONSTRAINT chk_idempotency_keys_status_range CHECK (response_status IS NULL OR response_status BETWEEN 200 AND 299)
);
COMMENT ON TABLE idempotency_keys IS 'One row per Idempotency-Key a user sent to a creating route. A repeat with the same body replays the first result, a repeat with another body is refused with 409. Rows older than 24 hours are deleted. Serves US-00-001, US-00-002, US-00-007.';
COMMENT ON COLUMN idempotency_keys.user_id IS 'The caller; a key is scoped to its user so two users cannot collide.';
COMMENT ON COLUMN idempotency_keys.key IS 'The UUID the client made once per logical operation and reuses on every retry.';
COMMENT ON COLUMN idempotency_keys.operation IS 'Which creating route the key was used on.';
COMMENT ON COLUMN idempotency_keys.request_hash IS 'SHA-256 of the request body (for an upload, of the file bytes), to tell a retry from a different request.';
COMMENT ON COLUMN idempotency_keys.response_status IS 'Status of the first response, null while the first request is still running.';
COMMENT ON COLUMN idempotency_keys.resource_id IS 'Id of the import, document or decision the first request created, so a replay re-reads it. No personal data is stored here.';
COMMENT ON COLUMN idempotency_keys.created_at IS 'When the first request arrived, used by the 24 hour sweeper.';
-- The sweeper deletes keys older than 24 hours.
CREATE INDEX idx_idempotency_keys_created_at ON idempotency_keys (created_at);

-- export_audit: who exported applicant data and how many rows, append-only.
-- Serves US-00-009
CREATE TABLE export_audit (
    id bigint GENERATED ALWAYS AS IDENTITY,
    exported_by uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    row_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT export_audit_pkey PRIMARY KEY (id),
    CONSTRAINT chk_export_audit_row_count_not_negative CHECK (row_count >= 0)
);
COMMENT ON TABLE export_audit IS 'One row per export of the verified list: who, when and how many rows. Never updated or deleted by the application. Serves US-00-009 and threat T-23.';
COMMENT ON COLUMN export_audit.id IS 'Surrogate key.';
COMMENT ON COLUMN export_audit.exported_by IS 'The staff member who downloaded the file. RESTRICT keeps the history.';
COMMENT ON COLUMN export_audit.row_count IS 'Number of Verified applications in the file.';
COMMENT ON COLUMN export_audit.created_at IS 'When the export ran.';
-- Foreign-key index: exports by one user.
CREATE INDEX idx_export_audit_exported_by ON export_audit (exported_by);

-- imports: one run of the applications CSV import.
-- Serves US-00-001
CREATE TABLE imports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    uploaded_by uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    source_name text NOT NULL,
    rows_read integer NOT NULL,
    rows_created integer NOT NULL,
    rows_rejected integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT imports_pkey PRIMARY KEY (id),
    CONSTRAINT chk_imports_counts_consistent CHECK (rows_read >= 0 AND rows_created >= 0 AND rows_rejected >= 0 AND rows_created + rows_rejected = rows_read),
    CONSTRAINT chk_imports_source_name_length CHECK (length(source_name) <= 255)
);
COMMENT ON TABLE imports IS 'One CSV import run with its counts. Serves US-00-001.';
COMMENT ON COLUMN imports.id IS 'Surrogate key.';
COMMENT ON COLUMN imports.uploaded_by IS 'The staff member who ran the import.';
COMMENT ON COLUMN imports.source_name IS 'File name as uploaded.';
COMMENT ON COLUMN imports.rows_read IS 'Data rows in the file, header excluded.';
COMMENT ON COLUMN imports.rows_created IS 'Rows that became applications.';
COMMENT ON COLUMN imports.rows_rejected IS 'Rows refused, each listed in import_row_errors.';
COMMENT ON COLUMN imports.created_at IS 'When the import ran.';
-- Foreign-key index: imports by uploader.
CREATE INDEX idx_imports_uploaded_by ON imports (uploaded_by);

-- import_row_errors: why a row of an import was refused.
-- Serves US-00-001
CREATE TABLE import_row_errors (
    id bigint GENERATED ALWAYS AS IDENTITY,
    import_id uuid NOT NULL REFERENCES imports (id) ON DELETE CASCADE,
    row_number integer NOT NULL,
    column_name text,
    reason_code text NOT NULL,
    CONSTRAINT import_row_errors_pkey PRIMARY KEY (id),
    CONSTRAINT chk_import_row_errors_row_number_positive CHECK (row_number >= 1),
    CONSTRAINT chk_import_row_errors_reason_code CHECK (reason_code IN ('missing_value', 'bad_date', 'bad_marks', 'duplicate_application_ref', 'too_long', 'out_of_range', 'malformed_row'))
);
COMMENT ON TABLE import_row_errors IS 'A refused CSV row: its number, the column and a reason code, never the value. Serves US-00-001.';
COMMENT ON COLUMN import_row_errors.id IS 'Surrogate key.';
COMMENT ON COLUMN import_row_errors.import_id IS 'The import this error belongs to.';
COMMENT ON COLUMN import_row_errors.row_number IS 'Line number in the file, counting the header as line 1.';
COMMENT ON COLUMN import_row_errors.column_name IS 'The column at fault, null when the whole row is.';
COMMENT ON COLUMN import_row_errors.reason_code IS 'Closed set of reasons. The offending value is not stored so no personal data enters this table.';
-- Foreign-key index: the errors of one import, shown after upload.
CREATE INDEX idx_import_row_errors_import_id ON import_row_errors (import_id, row_number);

-- applications: one applicant record from the CSV, with its status.
-- Serves US-00-001, US-00-004, US-00-005, US-00-006, US-00-008, US-00-009
CREATE TABLE applications (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    import_id uuid REFERENCES imports (id) ON DELETE SET NULL,
    application_ref text NOT NULL,
    full_name text NOT NULL,
    father_name text NOT NULL,
    date_of_birth date NOT NULL,
    board text NOT NULL,
    roll_number text NOT NULL,
    marks jsonb NOT NULL,
    category text NOT NULL,
    status application_status NOT NULL DEFAULT 'missing_documents',
    rejected_at timestamptz,
    erased_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT applications_pkey PRIMARY KEY (id),
    CONSTRAINT chk_applications_ref_not_blank CHECK (btrim(application_ref) <> ''),
    CONSTRAINT chk_applications_full_name_not_blank CHECK (btrim(full_name) <> ''),
    CONSTRAINT chk_applications_dob_range CHECK (date_of_birth BETWEEN DATE '1950-01-01' AND DATE '2020-12-31'),
    CONSTRAINT chk_applications_marks_is_object CHECK (jsonb_typeof(marks) = 'object'),
    CONSTRAINT chk_applications_rejected_in_review CHECK (rejected_at IS NULL OR status = 'needs_review'),
    CONSTRAINT chk_applications_text_lengths CHECK (length(application_ref) <= 40 AND length(full_name) <= 120 AND length(father_name) <= 120 AND length(board) <= 80 AND length(roll_number) <= 30 AND length(category) <= 40)
);
COMMENT ON TABLE applications IS 'An applicant record as the admissions office supplied it, plus its verification status. Serves US-00-001, US-00-004, US-00-005, US-00-006, US-00-008, US-00-009.';
COMMENT ON COLUMN applications.id IS 'Surrogate key used in URLs.';
COMMENT ON COLUMN applications.import_id IS 'The import that created this record, null if the import log is purged.';
COMMENT ON COLUMN applications.application_ref IS 'The application id from the CSV, unique. [personal data]';
COMMENT ON COLUMN applications.full_name IS 'Applicant name as supplied. [personal data]';
COMMENT ON COLUMN applications.father_name IS 'Father name as supplied. [personal data]';
COMMENT ON COLUMN applications.date_of_birth IS 'Date of birth, a minor in most records. [personal data]';
COMMENT ON COLUMN applications.board IS 'Examination board name.';
COMMENT ON COLUMN applications.roll_number IS 'Roll number on the marksheet. [personal data]';
COMMENT ON COLUMN applications.marks IS 'Marks by subject as a JSON object of subject to integer. [personal data]';
COMMENT ON COLUMN applications.category IS 'Admission category, a community attribute. [personal data]';
COMMENT ON COLUMN applications.status IS 'verified, needs_review or missing_documents, exactly one at all times.';
COMMENT ON COLUMN applications.rejected_at IS 'Set when a verifier rejects. The application stays needs_review but leaves the queue.';
COMMENT ON COLUMN applications.erased_at IS 'Set when the personal columns were replaced by placeholders after an erasure request. The row stays so the decision log keeps its parent.';
COMMENT ON COLUMN applications.created_at IS 'When the record was imported.';
COMMENT ON COLUMN applications.updated_at IS 'Last status or data change, orders the review queue.';
-- The CSV application id is unique, a duplicate row is refused at import.
CREATE UNIQUE INDEX uq_applications_application_ref ON applications (application_ref);
-- Foreign-key index: applications created by one import.
CREATE INDEX idx_applications_import_id ON applications (import_id);
-- The review queue: needs_review, not rejected and not erased, oldest change first. Queries repeat the predicate.
CREATE INDEX idx_applications_review_queue ON applications (updated_at, id) WHERE status = 'needs_review' AND rejected_at IS NULL AND erased_at IS NULL;

-- documents: one uploaded scan, its type and processing state.
-- Serves US-00-002, US-00-003, US-00-005
CREATE TABLE documents (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    uploaded_by uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    source_content_type text NOT NULL,
    detected_type document_type,
    status document_status NOT NULL DEFAULT 'uploaded',
    failure_reason text,
    is_current boolean NOT NULL DEFAULT true,
    sha256 text NOT NULL,
    size_bytes integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT documents_pkey PRIMARY KEY (id),
    CONSTRAINT chk_documents_content_type CHECK (source_content_type IN ('image/jpeg', 'image/png', 'application/pdf')),
    CONSTRAINT chk_documents_sha256_hex CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_documents_size_range CHECK (size_bytes BETWEEN 1 AND 8388608),
    CONSTRAINT chk_documents_failure_only_when_failed CHECK (failure_reason IS NULL OR status = 'failed'),
    CONSTRAINT chk_documents_text_lengths CHECK (failure_reason IS NULL OR length(failure_reason) <= 120)
);
COMMENT ON TABLE documents IS 'One uploaded scan or photo for an application. Serves US-00-002, US-00-003, US-00-005.';
COMMENT ON COLUMN documents.id IS 'Surrogate key used in URLs.';
COMMENT ON COLUMN documents.application_id IS 'The application this document belongs to. Documents go with their application.';
COMMENT ON COLUMN documents.uploaded_by IS 'The staff member who uploaded it.';
COMMENT ON COLUMN documents.source_content_type IS 'image/jpeg, image/png or application/pdf, the only accepted formats.';
COMMENT ON COLUMN documents.detected_type IS 'Document type found by the engine, null until processed, unknown if not recognised.';
COMMENT ON COLUMN documents.status IS 'uploaded, processing, read or failed.';
COMMENT ON COLUMN documents.failure_reason IS 'A short reason code when processing failed, never document content.';
COMMENT ON COLUMN documents.is_current IS 'False once a newer document of the same type replaced it. The older one is kept.';
COMMENT ON COLUMN documents.sha256 IS 'SHA-256 of the uploaded bytes, hex, to spot a repeated upload.';
COMMENT ON COLUMN documents.size_bytes IS 'Size of the uploaded file in bytes, at most 8 MiB.';
COMMENT ON COLUMN documents.created_at IS 'When the file was uploaded.';
COMMENT ON COLUMN documents.updated_at IS 'Last status change.';
-- Foreign-key index: the documents of one application, newest first for the review screen.
CREATE INDEX idx_documents_application_id ON documents (application_id, created_at DESC);
-- Foreign-key index: uploads by one user.
CREATE INDEX idx_documents_uploaded_by ON documents (uploaded_by);
-- At most one current document per application and type, so a re-upload replaces and keeps the old one.
CREATE UNIQUE INDEX uq_documents_current_type ON documents (application_id, detected_type) WHERE is_current AND detected_type IS NOT NULL AND detected_type <> 'unknown';
-- The processing loop claims the oldest uploaded document. The claim query repeats status = 'uploaded' and orders by created_at.
CREATE INDEX idx_documents_uploaded_created_at ON documents (created_at) WHERE status = 'uploaded';

-- document_blobs: the image bytes, kept apart so the documents table stays narrow.
-- Serves US-00-002, US-00-006
CREATE TABLE document_blobs (
    document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    content_type text NOT NULL,
    content bytea NOT NULL,
    CONSTRAINT document_blobs_pkey PRIMARY KEY (document_id),
    CONSTRAINT chk_document_blobs_content_type CHECK (content_type IN ('image/jpeg', 'image/png')),
    CONSTRAINT chk_document_blobs_size_range CHECK (octet_length(content) BETWEEN 1 AND 8388608)
);
COMMENT ON TABLE document_blobs IS 'The page image used for reading, behind a storage interface so object storage can replace this table later. Serves US-00-002, US-00-006.';
COMMENT ON COLUMN document_blobs.document_id IS 'The document these bytes belong to, one-to-one.';
COMMENT ON COLUMN document_blobs.content_type IS 'image/png or image/jpeg. A PDF is stored as its first page rasterised to JPEG at no more than 200 dpi so it stays under the size cap. The original PDF is not kept.';
COMMENT ON COLUMN document_blobs.content IS 'The image bytes. [personal data]';

-- extracted_fields: one value read from a document, with its comparison.
-- Serves US-00-003, US-00-004, US-00-005, US-00-006, US-00-007
CREATE TABLE extracted_fields (
    id bigint GENERATED ALWAYS AS IDENTITY,
    document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    field_name field_name NOT NULL,
    subject text,
    value text NOT NULL DEFAULT '',
    confidence real,
    box jsonb,
    match_result match_result,
    needs_review boolean NOT NULL DEFAULT false,
    review_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT extracted_fields_pkey PRIMARY KEY (id),
    CONSTRAINT chk_extracted_fields_subject_only_for_marks CHECK ((field_name = 'marks') = (subject IS NOT NULL)),
    CONSTRAINT chk_extracted_fields_confidence_range CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT chk_extracted_fields_review_flag_matches_reason CHECK (needs_review = (review_reason IS NOT NULL)),
    CONSTRAINT chk_extracted_fields_review_reason_known CHECK (review_reason IS NULL OR review_reason IN ('low_confidence', 'format_invalid', 'mismatch', 'not_extracted')),
    CONSTRAINT chk_extracted_fields_text_lengths CHECK (length(value) <= 200 AND (subject IS NULL OR length(subject) <= 80))
);
COMMENT ON TABLE extracted_fields IS 'One field the engine read from a document: value, confidence, position and how it compared with the application. Marks have one row per subject. Serves US-00-003, US-00-004, US-00-005, US-00-006, US-00-007.';
COMMENT ON COLUMN extracted_fields.id IS 'Surrogate key.';
COMMENT ON COLUMN extracted_fields.document_id IS 'The document the value was read from.';
COMMENT ON COLUMN extracted_fields.field_name IS 'Which field: name, father_name, dob, board, roll_number, marks or document_number.';
COMMENT ON COLUMN extracted_fields.subject IS 'The subject for a marks row, null for every other field.';
COMMENT ON COLUMN extracted_fields.value IS 'The current value, after any verifier correction. The value the engine read is kept in the decisions row of the correction. [personal data]';
COMMENT ON COLUMN extracted_fields.confidence IS 'Engine confidence for the lines the value came from, 0 to 1, null when not available.';
COMMENT ON COLUMN extracted_fields.box IS 'Where the value sits on the page, for the side-by-side view and field crops.';
COMMENT ON COLUMN extracted_fields.match_result IS 'match, mismatch or skipped against the application value, null until compared.';
COMMENT ON COLUMN extracted_fields.needs_review IS 'True when the field sends the application to Needs review.';
COMMENT ON COLUMN extracted_fields.review_reason IS 'low_confidence, format_invalid, mismatch or not_extracted, set exactly when needs_review is true.';
COMMENT ON COLUMN extracted_fields.created_at IS 'When the field was read.';
COMMENT ON COLUMN extracted_fields.updated_at IS 'Last correction or comparison.';
-- One row per field per document, and per subject for marks. Also serves the per-document field list.
CREATE UNIQUE INDEX uq_extracted_fields_document_field ON extracted_fields (document_id, field_name, coalesce(subject, ''));

-- gateway_calls: one row per call to the OCR gateway.
-- Serves US-02-001
CREATE TABLE gateway_calls (
    id bigint GENERATED ALWAYS AS IDENTITY,
    document_id uuid REFERENCES documents (id) ON DELETE SET NULL,
    engine text NOT NULL,
    engine_version text NOT NULL,
    preprocess boolean NOT NULL,
    image_max_side integer,
    duration_ms integer NOT NULL,
    outcome call_outcome NOT NULL,
    units integer,
    cost numeric(10, 4) NOT NULL DEFAULT 0,
    error_class text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT gateway_calls_pkey PRIMARY KEY (id),
    CONSTRAINT chk_gateway_calls_cost_zero CHECK (cost = 0),
    CONSTRAINT chk_gateway_calls_duration_nonnegative CHECK (duration_ms >= 0),
    CONSTRAINT chk_gateway_calls_error_class_only_on_failure CHECK (error_class IS NULL OR outcome <> 'ok'),
    CONSTRAINT chk_gateway_calls_text_lengths CHECK (length(engine) <= 40 AND length(engine_version) <= 40 AND (error_class IS NULL OR length(error_class) <= 80))
);
COMMENT ON TABLE gateway_calls IS 'The log of engine calls. Its row count is the running call count the cap is checked against, and it survives restarts. Serves US-02-001.';
COMMENT ON COLUMN gateway_calls.id IS 'Surrogate key.';
COMMENT ON COLUMN gateway_calls.document_id IS 'The document read, null if the document was deleted. The call stays counted.';
COMMENT ON COLUMN gateway_calls.engine IS 'Engine name, for example rapidocr.';
COMMENT ON COLUMN gateway_calls.engine_version IS 'Engine and model version, so a result can be traced to what produced it.';
COMMENT ON COLUMN gateway_calls.preprocess IS 'Whether the OpenCV preprocessing ran first.';
COMMENT ON COLUMN gateway_calls.image_max_side IS 'Longest image side in pixels after the cap, null if none.';
COMMENT ON COLUMN gateway_calls.duration_ms IS 'Wall time of the call in milliseconds.';
COMMENT ON COLUMN gateway_calls.outcome IS 'pending while the engine runs, then ok or error, or refused when the call cap was reached. The pending row is committed before the call so the call is logged even if the process dies.';
COMMENT ON COLUMN gateway_calls.units IS 'Text lines returned, the unit count the gateway logs.';
COMMENT ON COLUMN gateway_calls.cost IS 'Always zero: no paid engine is allowed.';
COMMENT ON COLUMN gateway_calls.error_class IS 'Exception class name on failure, never a message that could hold document text.';
COMMENT ON COLUMN gateway_calls.created_at IS 'When the call was made.';
-- Foreign-key index: the calls for one document.
CREATE INDEX idx_gateway_calls_document_id ON gateway_calls (document_id);
-- Exactly one successful call per document, a retry after an error is allowed.
CREATE UNIQUE INDEX uq_gateway_calls_document_ok ON gateway_calls (document_id) WHERE outcome = 'ok';

-- decisions: the append-only log of verifier decisions.
-- Serves US-00-007
CREATE TABLE decisions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL REFERENCES applications (id) ON DELETE RESTRICT,
    decided_by uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    extracted_field_id bigint REFERENCES extracted_fields (id) ON DELETE SET NULL,
    action decision_action NOT NULL,
    reason text,
    field_name field_name,
    subject text,
    old_value text,
    new_value text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT decisions_pkey PRIMARY KEY (id),
    CONSTRAINT chk_decisions_reject_needs_reason CHECK (action <> 'reject' OR (reason IS NOT NULL AND btrim(reason) <> '')),
    CONSTRAINT chk_decisions_correct_needs_values CHECK (action <> 'correct' OR (field_name IS NOT NULL AND old_value IS NOT NULL AND new_value IS NOT NULL)),
    CONSTRAINT chk_decisions_text_lengths CHECK ((reason IS NULL OR length(reason) <= 1000) AND (old_value IS NULL OR length(old_value) <= 200) AND (new_value IS NULL OR length(new_value) <= 200) AND (subject IS NULL OR length(subject) <= 80))
);
COMMENT ON TABLE decisions IS 'Who approved, corrected or rejected an application, when and why. Rows are never deleted or truncated, and only the free-text columns can be replaced by an erased marker. Serves US-00-007.';
COMMENT ON COLUMN decisions.id IS 'Surrogate key.';
COMMENT ON COLUMN decisions.application_id IS 'The application decided. RESTRICT so the record cannot disappear with it.';
COMMENT ON COLUMN decisions.decided_by IS 'The verifier who decided.';
COMMENT ON COLUMN decisions.extracted_field_id IS 'For a correction, the exact field of the exact document that was changed, since an application can have a name on several documents. Null for approve and reject, and null after the document is erased.';
COMMENT ON COLUMN decisions.action IS 'approve, correct or reject.';
COMMENT ON COLUMN decisions.reason IS 'Required for a reject, free text a verifier typed. [personal data]';
COMMENT ON COLUMN decisions.field_name IS 'For a correction, the field changed.';
COMMENT ON COLUMN decisions.subject IS 'For a marks correction, the subject.';
COMMENT ON COLUMN decisions.old_value IS 'For a correction, the value before. [personal data]';
COMMENT ON COLUMN decisions.new_value IS 'For a correction, the value after. [personal data]';
COMMENT ON COLUMN decisions.created_at IS 'When the decision was made.';
-- Foreign-key index: the decision history of one application.
CREATE INDEX idx_decisions_application_id ON decisions (application_id, created_at);
-- Foreign-key index: decisions by one verifier.
CREATE INDEX idx_decisions_decided_by ON decisions (decided_by);
-- Foreign-key index: the corrections made to one extracted field, and no table scan when a field row is deleted.
CREATE INDEX idx_decisions_extracted_field_id ON decisions (extracted_field_id);

CREATE FUNCTION decisions_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'decisions rows cannot be deleted';
    END IF;
    IF NEW.id <> OLD.id OR NEW.application_id <> OLD.application_id OR NEW.decided_by <> OLD.decided_by
       OR NEW.action <> OLD.action OR NEW.field_name IS DISTINCT FROM OLD.field_name
       OR NEW.subject IS DISTINCT FROM OLD.subject OR NEW.created_at <> OLD.created_at
       OR (NEW.extracted_field_id IS DISTINCT FROM OLD.extracted_field_id AND NEW.extracted_field_id IS NOT NULL) THEN
        RAISE EXCEPTION 'decisions rows may only be anonymised';
    END IF;
    IF (NEW.reason IS DISTINCT FROM OLD.reason AND NEW.reason IS DISTINCT FROM '[erased]')
       OR (NEW.old_value IS DISTINCT FROM OLD.old_value AND NEW.old_value IS DISTINCT FROM '[erased]')
       OR (NEW.new_value IS DISTINCT FROM OLD.new_value AND NEW.new_value IS DISTINCT FROM '[erased]') THEN
        RAISE EXCEPTION 'decisions text may only be replaced by the erased marker';
    END IF;
    RETURN NEW;
END;
$$;
-- Append-only: no delete, and the only updates allowed replace the free-text columns with '[erased]' or null the field link.
CREATE TRIGGER trg_decisions_append_only BEFORE UPDATE OR DELETE ON decisions FOR EACH ROW EXECUTE FUNCTION decisions_guard();

CREATE FUNCTION decisions_refuse_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'decisions cannot be truncated';
END;
$$;
-- A row trigger does not fire on TRUNCATE, so the log needs a statement trigger as well.
CREATE TRIGGER trg_decisions_no_truncate BEFORE TRUNCATE ON decisions FOR EACH STATEMENT EXECUTE FUNCTION decisions_refuse_truncate();

COMMIT;
