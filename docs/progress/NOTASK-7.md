# NOTASK-7: accounts sign up, fix wave

## Changed
- docs/security/AUTH.md: deployment contract for the source address (trust only the proxy, overwrite X-Forwarded-For, one worker), who a decision names, no Origin or CSRF check on register and login, last reviewed line.
- docs/adr/0013-open-sign-up-with-a-self-chosen-role.md and docs/security/threat-model-docket.md (T-38): the shown name is self-chosen and not unique; the user id is the true actor. Residual line for login CSRF and quota spending.
- .env.example: comment next to the register settings.
- api/openapi.yaml: 401 on registerUser.
- docs/security/permission-matrix.md: register 409, 422 and 429 rows, cell count 37.
- docs/design/docket-hld.md: corrected the "no auth code exists" sentence.
- frontend/src/features/auth/notices.ts and screens/S-01b-sign-up.screen.tsx: 409 body is "Choose another, or sign in if this was you."

## Verified
- frontend `make check`: 5 gates run, 0 skipped, passed.
- backend `make lint typecheck test`: 446 passed, coverage 81.24%.

## Not done
- Backend `make check` fails at format-check on docs/superpowers/plans/2026-10-07-accounts-sign-up.md:311 (a file this wave did not touch); not fixed.
- Browser check and accessibility audit of the sign up screen: not run.
- Origin allow-list on register and login, shared limiter store: follow-ups, no code changed.

## Noticed
- The format-check failure above predates this wave.
