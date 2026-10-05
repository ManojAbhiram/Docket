# Entity relationship diagram: Docket

PostgreSQL. 12 tables, 14 relationships.

## Diagram

```mermaid
erDiagram
    users ||--o{ sessions : "signs in as"
    users ||--o{ idempotency_keys : "sends"
    users ||--o{ export_audit : "exports as"
    users ||--o{ imports : "runs"
    users ||--o{ documents : "uploads"
    users ||--o{ decisions : "makes"
    imports ||--o{ import_row_errors : "refuses rows with"
    imports |o--o{ applications : "creates"
    applications ||--o{ documents : "has"
    applications ||--o{ decisions : "is decided by"
    documents ||--|| document_blobs : "stores image in"
    documents ||--o{ extracted_fields : "is read into"
    documents |o--o{ gateway_calls : "is read by"
    extracted_fields |o--o{ decisions : "is corrected by"
    users {
        uuid id PK "Surrogate key"
        text username UK "Sign-in name (personal data)"
        text display_name "Shown in the log (personal data)"
        user_role role "staff or verifier"
        text password_hash "Argon2id"
        boolean is_active "False blocks sign-in"
        integer session_version "Logout everywhere"
        timestamptz last_login_at
        timestamptz created_at
        timestamptz updated_at
    }
    sessions {
        uuid id PK
        uuid user_id FK "Owner"
        bytea token_hash UK "SHA-256 of the cookie token"
        integer session_version
        timestamptz created_at
        timestamptz last_seen_at "Idle timeout"
        timestamptz expires_at "Absolute end"
        timestamptz revoked_at
    }
    idempotency_keys {
        uuid user_id PK "Caller"
        uuid key PK "Client UUID per operation"
        text operation
        bytea request_hash "SHA-256 of the body"
        smallint response_status "Null while running"
        uuid resource_id "What the first request created"
        timestamptz created_at "24 hour expiry"
    }
    export_audit {
        bigint id PK
        uuid exported_by FK "Staff member"
        integer row_count
        timestamptz created_at
    }
    imports {
        uuid id PK
        uuid uploaded_by FK "Staff member"
        text source_name
        integer rows_read
        integer rows_created
        integer rows_rejected
        timestamptz created_at
    }
    import_row_errors {
        bigint id PK
        uuid import_id FK
        integer row_number
        text column_name
        text reason_code "No value stored"
    }
    applications {
        uuid id PK
        uuid import_id FK "Null if log purged"
        text application_ref UK "CSV application id (personal data)"
        text full_name "Personal data"
        text father_name "Personal data"
        date date_of_birth "Personal data"
        text board
        text roll_number "Personal data"
        jsonb marks "Subject to marks (personal data)"
        text category "Personal data"
        application_status status "verified, needs_review, missing_documents"
        timestamptz rejected_at "Leaves the queue"
        timestamptz erased_at "Personal data erased in place"
        timestamptz created_at
        timestamptz updated_at
    }
    documents {
        uuid id PK
        uuid application_id FK
        uuid uploaded_by FK
        text source_content_type
        document_type detected_type "Null until read"
        document_status status
        text failure_reason "Code only"
        boolean is_current "False when replaced"
        text sha256
        integer size_bytes "At most 8 MiB"
        timestamptz created_at
        timestamptz updated_at
    }
    document_blobs {
        uuid document_id PK "One-to-one with documents"
        text content_type
        bytea content "Image bytes (personal data)"
    }
    extracted_fields {
        bigint id PK
        uuid document_id FK
        field_name field_name "Which field"
        text subject "Marks only"
        text value "Current value (personal data)"
        real confidence "0 to 1"
        jsonb box "Position on the page"
        match_result match_result
        boolean needs_review
        text review_reason
        timestamptz created_at
        timestamptz updated_at
    }
    gateway_calls {
        bigint id PK
        uuid document_id FK "Null if document deleted"
        text engine
        text engine_version
        boolean preprocess
        integer image_max_side
        integer duration_ms
        call_outcome outcome
        integer units
        numeric cost "Always 0"
        text error_class
        timestamptz created_at
    }
    decisions {
        uuid id PK
        uuid application_id FK
        uuid decided_by FK
        bigint extracted_field_id FK "Which field a correction changed"
        decision_action action
        text reason "Personal data"
        field_name field_name
        text subject
        text old_value "Personal data"
        text new_value "Personal data"
        timestamptz created_at
    }
```

## Relationships

| From | | To | Meaning |
| --- | --- | --- | --- |
| users | one-to-many | sessions | A user can be signed in on several browsers. Deleting a user deletes the sessions (CASCADE), though users are deactivated, not deleted. |
| users | one-to-many | idempotency_keys | A user's creating requests are remembered for 24 hours so a retry replays the first result. CASCADE because a key means nothing without its user. |
| users | one-to-many | export_audit | Every export of the verified list names who made it. RESTRICT keeps that history. |
| users | one-to-many | imports | Every import names the staff member who ran it. RESTRICT keeps that history. |
| users | one-to-many | documents | Every upload names who made it. RESTRICT keeps that history. |
| users | one-to-many | decisions | Every decision names the verifier who made it. RESTRICT so the log never loses its author. |
| imports | one-to-many | import_row_errors | An import lists its refused rows. CASCADE removes them with the import. |
| imports | zero-or-one to many | applications | An application knows which import created it. SET NULL so purging the import log keeps the applicants. |
| applications | one-to-many | documents | An application has any number of documents, one current per type; replaced ones are kept. CASCADE because documents are the applicant's personal data and go with the record. |
| applications | one-to-many | decisions | An application has a history of decisions. RESTRICT so an application with a log cannot be deleted without first deciding what happens to the log (see the open concern on erasure). |
| documents | one-to-one | document_blobs | The image bytes of a document, kept apart. CASCADE removes the bytes with the document. |
| documents | one-to-many | extracted_fields | A document is read into one row per field and one per subject for marks. CASCADE because they are derived from it. |
| documents | zero-or-one to many | gateway_calls | A document is read by one successful call and any failed ones. SET NULL so the call count survives a deleted document. |
| extracted_fields | zero-or-one to many | decisions | A correction names the exact field of the exact document it changed, since an application can have a name on several documents. SET NULL so erasing a document does not break the log. |

`sessions`, `imports` and `import_row_errors` are not related to the applicant tables except through `applications.import_id`: they exist for sign-in and for reporting what an import refused.
