# Docket API

The contract is `api/openapi.yaml` (OpenAPI 3.1). It is a design: only `GET /healthz` and `GET /readyz` exist in code today (`app/api/health/router.py:34`, `app/api/health/router.py:40`).

## Where things are

| What | Where |
| --- | --- |
| Spec | `api/openapi.yaml` |
| Readable design | `docs/api/API.md`, generated, never edited by hand |
| Docs route | `/docs` and `/openapi.json`, non-production only (`app/main.py:46`, as recorded in `docs/security/AUTH.md`). Production does not mount them. |
| Style rules | the Bearing `openapi-spec` style reference, with the project deviations in the spec's `info.x-conventions` |

## Project conventions that differ from the style reference

1. No `/v1` in the path. One first-party client ships with the API.
2. The error `details` field is an object, as `app/core/errors.py` already returns.
3. A request that fails validation returns 422 `validation_error`, as the existing handler does.

## Regenerate the readable design

```
uv run --quiet --with pyyaml==6.0.3 python "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/openapi-spec/scripts/api_doc.py" --spec api/openapi.yaml --style "/home/manoj-abhiram-k/bearing/plugins/bearing/skills/openapi-spec/references/api-style.md" --out docs/api/API.md
```

## Lint

```
npx @redocly/cli@2.54.3 lint api/openapi.yaml
```

## Not yet in place

- The `api-conformance` Makefile target and CI job: no route except health exists to run against.
- Anti-forgery token mechanism (`X-CSRF-Token`): a pending story from the threat model (T-03).
