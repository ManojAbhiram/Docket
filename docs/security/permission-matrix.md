# Permission matrix: Docket

One row per cell. `Expected` is the HTTP status for that role acting on a resource. Every row has a test named `TC-AUTH-<role>-<resource>-<action>`, to be generated when the routes exist; none exists yet because no route exists.

Roles: anonymous, staff, verifier (and two session-state cases: a deactivated user and a stale session version). Resources: session, import, application, document, decision, dashboard, export, health, docs. Tenant column present: no (single office). Column "Own / other" reads `any` because there is no per-record owner; `unknown id` is a record that does not exist; `production` is the deployed environment.

A role denial is 403, because both roles know every route exists. An unknown id is 404 for every allowed role. A missing or invalid session is 401.

| Role | Resource | Action | Own / other / cross-tenant | Expected | Test |
| --- | --- | --- | --- | --- | --- |
| anonymous | session | login | any | 200 | TC-AUTH-anonymous-session-login |
| anonymous | session | logout | any | 401 | TC-AUTH-anonymous-session-logout |
| anonymous | import | create | any | 401 | TC-AUTH-anonymous-import-create |
| anonymous | application | read | any | 401 | TC-AUTH-anonymous-application-read |
| anonymous | document | upload | any | 401 | TC-AUTH-anonymous-document-upload |
| anonymous | document | read | any | 401 | TC-AUTH-anonymous-document-read |
| anonymous | decision | create | any | 401 | TC-AUTH-anonymous-decision-create |
| anonymous | dashboard | read | any | 401 | TC-AUTH-anonymous-dashboard-read |
| anonymous | export | read | any | 401 | TC-AUTH-anonymous-export-read |
| anonymous | health | read | any | 200 | TC-AUTH-anonymous-health-read |
| anonymous | docs | read | production | 404 | TC-AUTH-anonymous-docs-read-production |
| staff | session | logout | any | 204 | TC-AUTH-staff-session-logout |
| staff | import | create | any | 201 | TC-AUTH-staff-import-create |
| staff | application | read | any | 200 | TC-AUTH-staff-application-read |
| staff | application | read | unknown id | 404 | TC-AUTH-staff-application-read-unknown |
| staff | document | upload | any | 202 | TC-AUTH-staff-document-upload |
| staff | document | read | any | 200 | TC-AUTH-staff-document-read |
| staff | document | read | unknown id | 404 | TC-AUTH-staff-document-read-unknown |
| staff | decision | create | any | 403 | TC-AUTH-staff-decision-create |
| staff | dashboard | read | any | 200 | TC-AUTH-staff-dashboard-read |
| staff | export | read | any | 200 | TC-AUTH-staff-export-read |
| verifier | session | logout | any | 204 | TC-AUTH-verifier-session-logout |
| verifier | import | create | any | 403 | TC-AUTH-verifier-import-create |
| verifier | application | read | any | 200 | TC-AUTH-verifier-application-read |
| verifier | application | read | unknown id | 404 | TC-AUTH-verifier-application-read-unknown |
| verifier | document | upload | any | 403 | TC-AUTH-verifier-document-upload |
| verifier | document | read | any | 200 | TC-AUTH-verifier-document-read |
| verifier | document | read | unknown id | 404 | TC-AUTH-verifier-document-read-unknown |
| verifier | decision | create | any | 201 | TC-AUTH-verifier-decision-create |
| verifier | dashboard | read | any | 200 | TC-AUTH-verifier-dashboard-read |
| verifier | export | read | any | 403 | TC-AUTH-verifier-export-read |
| deactivated user | application | read | any | 401 | TC-AUTH-deactivated-application-read |
| stale session version | decision | create | any | 401 | TC-AUTH-stale-decision-create |

Cells: 33. Covered by a test today: the session, role-gate, deactivated and stale-session behaviour, through a test-only router (`tests/integration/test_auth_api.py`). The import and application list cells are covered by `tests/integration/api/test_import.py` (US-00-001), the document upload and list cells by `tests/integration/api/test_documents.py` (US-00-002), and the application detail and document image cells by `tests/integration/api/test_application_detail.py` (US-00-006); the decision, decision, dashboard and export cells are still reserved, because those routes do not exist yet. Each gets its test when its route is built.
