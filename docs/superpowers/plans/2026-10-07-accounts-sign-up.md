# Accounts: open sign up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A visitor can register as staff or verifier from a Sign up screen and is signed in at once.

**Architecture:** `POST /auth/register` reuses the existing sign-in machinery: Argon2 `Passwords`, the `hash_slots` semaphore, `SqlAuthStore.create_user` (already built for seeding) and the same two cookies. New pure rules and a `RegistrationLimiter` go in `app/domain/auth.py`. The front end adds a Sign up page next to Sign in in `frontend/src/features/auth`.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 async, argon2, pytest; React, TanStack Router and Query, zod, MSW, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-07-docket-completion-design.md` (Piece 1: accounts)

## Global Constraints

- Open registration with a self-chosen role was chosen by the engineer against the recommendation of invite-only accounts. Do not add an approval step or an access code unless asked.
- Zero cost, no new dependency (`CONSTRAINTS.md`, AGENTS.md rule 7).
- Username: lowercase, 3 to 64 characters, letters, digits, `.`, `_`, `-`. Unique ignoring case (database index `uq_users_username`).
- Password: 10 to 256 characters, not equal to the username.
- Display name: 1 to 120 characters after trimming (database check `chk_users_text_lengths`).
- No schema change. `users` already holds username, display_name, role, password_hash, and `create_user` exists in `app/db/repositories/auth.py`. If a task finds otherwise, stop: a schema change needs its own plan.
- No em dashes in anything written. Commits are Conventional with `[NOTASK-7]` at the end of the subject, with no AI attribution.
- Never push, merge or open a pull request. Print the command for the engineer.
- Python gate is `make check`; front-end gate is `cd frontend && make check`.

## Review Focus

- Registering a taken username in a different case (`Alice` vs `alice`): 409, never a second account. Pinned in Task 3.
- A 422 response must not echo the password. Pinned in Task 2.
- A burst of registrations from one source: 429 with `Retry-After`, and nothing created. Pinned in Task 2.
- A duplicate username costs the same hash work as a success, so timing does not separate them. Pinned in Task 2 (hash runs before `create_user`).
- Username padded with spaces or in capitals is stored trimmed and lowercase, and signs in afterwards. Pinned in Task 3.
- A role other than staff or verifier, or an extra field such as `is_active`, is refused with 422. Pinned in Task 2.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `app/domain/auth.py` (modify) | `check_username`, `check_password`, `check_display_name`, `RegistrationLimiter` |
| `app/core/config.py` (modify) | `register_max_per_source`, `register_window_minutes` |
| `app/api/auth/schemas.py` (modify) | `RegisterRequest` |
| `app/api/auth/router.py` (modify) | `POST /auth/register`, shared `_begin_session` helper |
| `app/main.py` (modify) | `app.state.register_limiter` |
| `tests/test_registration_domain.py` (create) | Rules and limiter, no database |
| `tests/test_register_route.py` (create) | 422 and 429 paths, no database |
| `tests/integration/test_auth_api.py` (modify) | Success, 409, sign in afterwards, both roles |
| `api/openapi.yaml`, `docs/security/*`, `docs/adr/0013-*` (modify/create) | Contract, matrix, threat model, decision record |
| `frontend/src/features/auth/*` (modify/create) | Schema, api, hook, notices, view, page, route, link, screen |

---

### Task 1: Registration rules and limiter

**Files:**
- Modify: `app/domain/auth.py`
- Test: `tests/test_registration_domain.py` (create)

**Interfaces:**
- Produces: `check_username(raw: str) -> str`, `check_password(password: str, username: str) -> str`, `check_display_name(raw: str) -> str` (each raises `ValueError` with a message safe to show), `RegistrationLimiter(max_per_source: int, window: timedelta, clock: Callable[[], datetime], max_entries: int = 10_000)` with `try_register(source: str) -> int | None` (None means allowed and the attempt is counted; an int is the seconds to wait).

- [ ] **Step 1: Write the failing tests**

```python
"""The registration rules and the per-source limiter (open sign up, ADR-0013). No database."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.auth import (
    RegistrationLimiter,
    check_display_name,
    check_password,
    check_username,
)


def test_a_username_is_trimmed_and_lowered() -> None:
    assert check_username("  Asha.K_9  ") == "asha.k_9"


@pytest.mark.parametrize("bad", ["ab", "a" * 65, "has space", "semi;colon", "ünï", ""])
def test_a_bad_username_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="username"):
        check_username(bad)


def test_a_password_needs_ten_characters() -> None:
    assert check_password("ten-chars!", "asha") == "ten-chars!"
    with pytest.raises(ValueError, match="at least 10"):
        check_password("nine-char", "asha")


def test_a_password_may_not_be_the_username_in_any_case() -> None:
    with pytest.raises(ValueError, match="username"):
        check_password("Asha.Kumar.1", "asha.kumar.1")


def test_a_display_name_is_trimmed_and_bounded() -> None:
    assert check_display_name("  Asha Kumar ") == "Asha Kumar"
    with pytest.raises(ValueError, match="name"):
        check_display_name("   ")
    with pytest.raises(ValueError, match="name"):
        check_display_name("x" * 121)


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def _limiter(clock: _Clock, max_entries: int = 10_000) -> RegistrationLimiter:
    return RegistrationLimiter(
        max_per_source=3, window=timedelta(hours=1), clock=clock, max_entries=max_entries
    )


def test_the_fourth_attempt_in_the_window_waits() -> None:
    clock = _Clock()
    limiter = _limiter(clock)
    assert [limiter.try_register("1.2.3.4") for _ in range(3)] == [None, None, None]
    wait = limiter.try_register("1.2.3.4")
    assert wait is not None and 0 < wait <= 3600


def test_another_source_is_not_affected() -> None:
    clock = _Clock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.try_register("1.2.3.4")
    assert limiter.try_register("5.6.7.8") is None


def test_the_window_slides() -> None:
    clock = _Clock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.try_register("1.2.3.4")
    clock.now += timedelta(hours=1, seconds=1)
    assert limiter.try_register("1.2.3.4") is None


def test_a_refused_attempt_is_not_counted() -> None:
    clock = _Clock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.try_register("1.2.3.4")
    for _ in range(50):
        limiter.try_register("1.2.3.4")
    clock.now += timedelta(hours=1, seconds=1)
    assert limiter.try_register("1.2.3.4") is None


def test_the_limiter_keeps_a_bounded_number_of_sources() -> None:
    limiter = _limiter(_Clock(), max_entries=5)
    for index in range(50):
        limiter.try_register(f"10.0.0.{index}")
    assert limiter.size() <= 5
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_registration_domain.py -q 2>&1 | tail -15`
Expected: FAIL with `ImportError: cannot import name 'RegistrationLimiter'`

- [ ] **Step 3: Implement**

At the top of `app/domain/auth.py` add `import re` beside the other imports. After the `Role` line add:

```python
USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,64}")
PASSWORD_MIN = 10
DISPLAY_NAME_MAX = 120


def check_username(raw: str) -> str:
    """The stored form of a username: trimmed and lower case, or ValueError."""
    name = raw.strip().lower()
    if not USERNAME_PATTERN.fullmatch(name):
        msg = "username must be 3 to 64 letters, digits, dots, dashes or underscores"
        raise ValueError(msg)
    return name


def check_password(password: str, username: str) -> str:
    """The password unchanged, or ValueError. The message never repeats the password."""
    if len(password) < PASSWORD_MIN:
        msg = f"password must be at least {PASSWORD_MIN} characters"
        raise ValueError(msg)
    if password.lower() == username.strip().lower():
        msg = "password must not be the same as the username"
        raise ValueError(msg)
    return password


def check_display_name(raw: str) -> str:
    """The name shown in the decision log, trimmed, or ValueError."""
    name = raw.strip()
    if not name or len(name) > DISPLAY_NAME_MAX:
        msg = f"name must be 1 to {DISPLAY_NAME_MAX} characters"
        raise ValueError(msg)
    return name
```

Append at the end of the file:

```python
class RegistrationLimiter:
    """Allows a few registrations per source per window. In memory, like LoginLimiter (ADR-0011).

    Only allowed attempts are counted, so a flood of refused ones does not extend its own wait. The
    number of sources kept is capped, because the sources come from whoever is attacking.
    """

    def __init__(
        self,
        *,
        max_per_source: int,
        window: timedelta,
        clock: Callable[[], datetime],
        max_entries: int = 10_000,
    ) -> None:
        self._max = max_per_source
        self._window = window
        self._clock = clock
        self._max_entries = max_entries
        self._attempts: dict[str, deque[datetime]] = {}

    def try_register(self, source: str) -> int | None:
        """None if this attempt may go ahead (and is counted), else the seconds to wait."""
        now = self._clock()
        attempts = self._attempts.pop(source, None) or deque()
        self._attempts[source] = attempts  # most recently used goes last
        while attempts and now - attempts[0] > self._window:
            attempts.popleft()
        wait: int | None = None
        if len(attempts) >= self._max:
            wait = max(1, math.ceil((attempts[0] + self._window - now).total_seconds()))
        else:
            attempts.append(now)
        while len(self._attempts) > self._max_entries:
            del self._attempts[next(iter(self._attempts))]
        return wait

    def size(self) -> int:
        return len(self._attempts)
```

Update the module docstring's first line to: `"""Passwords, session tokens, registration rules and the sign-in limiters (US-00-011, ADR-0006, ADR-0012, ADR-0013).`

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_registration_domain.py tests/test_auth_domain.py -q 2>&1 | tail -8`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add app/domain/auth.py tests/test_registration_domain.py
git commit -m "feat(auth): add the registration rules and limiter [NOTASK-7]"
```

---

### Task 2: The register endpoint

**Files:**
- Modify: `app/core/config.py` (after `login_hash_concurrency`), `app/api/auth/schemas.py`, `app/api/auth/router.py`, `app/main.py`
- Test: `tests/test_register_route.py` (create)

**Interfaces:**
- Consumes: Task 1 functions and `RegistrationLimiter`; existing `SqlAuthStore.create_user(username, display_name, role, password_hash) -> bool`, `find_user`, `start_session`.
- Produces: `POST /api/auth/register` (body `RegisterRequest`, 200 `UserOut` with both cookies; 409 `conflict`; 422; 429 with `Retry-After`), `app.state.register_limiter`.

- [ ] **Step 1: Write the failing tests** (`tests/test_register_route.py`, no database; every case here is answered before any database call)

```python
"""Register: the paths that are decided before the database is touched."""

from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.domain.auth import RegistrationLimiter

GOOD = {
    "username": "asha.k",
    "display_name": "Asha Kumar",
    "password": "a-long-phrase-1",
    "role": "staff",
}


@pytest.mark.parametrize(
    "change",
    [
        {"username": "ab"},
        {"password": "short"},
        {"password": "ASHA.K"},
        {"display_name": "   "},
        {"role": "admin"},
        {"is_active": True},
    ],
)
async def test_a_bad_body_is_refused_with_422(
    client: AsyncClient, change: dict[str, object]
) -> None:
    response = await client.post("/api/auth/register", json={**GOOD, **change})
    assert response.status_code == 422


async def test_a_422_never_echoes_the_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={**GOOD, "password": "tooshort", "username": "x"}
    )
    assert response.status_code == 422
    assert "tooshort" not in response.text


async def test_a_source_over_its_limit_gets_429(app: FastAPI, client: AsyncClient) -> None:
    app.state.register_limiter = RegistrationLimiter(
        max_per_source=0, window=timedelta(hours=1), clock=app.state.clock
    )
    response = await client.post("/api/auth/register", json=GOOD)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert response.json()["error"]["code"] == "too_many_attempts"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_register_route.py -q 2>&1 | tail -15`
Expected: FAIL, the route answers 404 or 405

- [ ] **Step 3: Implement**

`app/core/config.py`, after the `login_hash_concurrency` line:

```python
    register_max_per_source: int = Field(default=10, ge=0)
    register_window_minutes: int = Field(default=60, ge=1)
```

Add both to `.env.example` with their defaults and a comment, keeping that file's existing style.

`app/api/auth/schemas.py`: change the import to `from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator` and `from app.domain.auth import Role, check_display_name, check_password, check_username`, then add:

```python
class RegisterRequest(BaseModel):
    """Open sign up. The role is the person's own choice (ADR-0013). Nothing else is accepted."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(max_length=64)
    display_name: str = Field(max_length=120)
    password: str = Field(max_length=256)
    role: Role

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        return check_username(value)

    @field_validator("display_name")
    @classmethod
    def _display_name(cls, value: str) -> str:
        return check_display_name(value)

    @model_validator(mode="after")
    def _password(self) -> "RegisterRequest":
        check_password(self.password, self.username)
        return self
```

`app/api/auth/router.py`: import `RegisterRequest`, `ConflictError`, `RegistrationLimiter` and `Role`-free helpers as needed. Move the last five lines of `login` (token, `start_session`, two cookies) into a helper used by both routes:

```python
async def _begin_session(
    user: UserRecord,
    response: Response,
    store: SqlAuthStore,
    state: Any,
    settings: Settings,
) -> None:
    """Start a session for this user and set the session and anti-forgery cookies."""
    token = new_token()
    now = state.clock()
    lifetime = timedelta(hours=settings.session_absolute_hours)
    await store.start_session(user, hash_token(token), now=now, expires_at=now + lifetime)
    _set_cookie(response, SESSION_COOKIE, token, settings, http_only=True)
    _set_cookie(response, CSRF_COOKIE, csrf_for(token), settings, http_only=False)
```

(import `UserRecord` from `app.domain.auth`; `login` ends with `await _begin_session(user, response, store, state, settings)` then its `return`). Then add the route after `login`:

```python
@router.post(
    "/register",
    response_model=UserOut,
    responses={**_ERRORS, 409: {"model": ErrorEnvelope}, 429: {"model": ErrorEnvelope}},
)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    store: Annotated[SqlAuthStore, Depends(get_auth_store)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> UserOut:
    """Create an account with the chosen role and sign it in (ADR-0013).

    The password is hashed before the name is looked up, so a taken name costs the same work as a
    free one. A taken name answers 409, which does say that the name exists.
    """
    state = request.app.state
    limiter: RegistrationLimiter = state.register_limiter
    passwords: Passwords = state.passwords
    source = request.client.host if request.client else "unknown"
    wait = limiter.try_register(source)
    if wait is not None:
        raise TooManyAttemptsError(
            "too many sign ups from here, try again later", headers={"Retry-After": str(wait)}
        )
    async with state.hash_slots:
        stored = await asyncio.to_thread(passwords.hash, body.password)
    if not await store.create_user(body.username, body.display_name, body.role, stored):
        raise ConflictError("that username is taken")
    user = await store.find_user(body.username)
    if user is None:  # the row was deactivated or removed between the two statements
        raise UnauthorizedError("sign in to continue")
    await _begin_session(user, response, store, state, settings)
    return UserOut(id=user.id, display_name=user.display_name, role=user.role)
```

Update the module docstring to mention `/auth/register`.

`app/main.py`, in `_start_sign_in` after `login_limiter`:

```python
    app.state.register_limiter = RegistrationLimiter(
        max_per_source=settings.register_max_per_source,
        window=timedelta(minutes=settings.register_window_minutes),
        clock=lambda: app.state.clock(),
    )
```

and add `RegistrationLimiter` to the existing `app.domain.auth` import.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_register_route.py tests/test_auth_domain.py tests/test_registration_domain.py -q 2>&1 | tail -8`
Expected: all pass

- [ ] **Step 5: Gate and commit**

Run: `make check 2>&1 | tail -15` (expect the gate tally to show no failures)

```bash
git add app tests .env.example
git commit -m "feat(auth): add POST /auth/register with a per-source limit [NOTASK-7]"
```

---

### Task 3: Integration tests, contract, security docs, ADR

**Files:**
- Modify: `tests/integration/test_auth_api.py`, `api/openapi.yaml`, `docs/security/permission-matrix.md`, `docs/security/threat-model-docket.md`, `docs/security/AUTH.md`
- Create: `docs/adr/0013-open-sign-up-with-a-self-chosen-role.md`

**Interfaces:**
- Consumes: the endpoint from Task 2; helpers `sign_in`, `SAME_ORIGIN` in `tests/integration/helpers.py`.

- [ ] **Step 1: Write the integration tests.** Add to `tests/integration/test_auth_api.py`, using the fixtures that file already uses for `client` (read the file first and copy the way an existing test requests a client and a connection):

```python
REGISTER = {
    "username": "  Asha.K  ",
    "display_name": "Asha Kumar",
    "password": "a-long-phrase-1",
    "role": "verifier",
}


async def test_registering_signs_the_person_in_with_the_chosen_role(client: AsyncClient) -> None:
    response = await client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 200
    assert response.json()["role"] == "verifier"
    assert "docket_session" in client.cookies and "docket_csrf" in client.cookies
    me = await client.get("/api/auth/me")
    assert me.json()["display_name"] == "Asha Kumar"


async def test_the_name_is_stored_trimmed_and_lower_case_and_signs_in_later(
    client: AsyncClient,
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    client.cookies.clear()
    again = await sign_in(client, "asha.k", "a-long-phrase-1")
    assert again.status_code == 200


async def test_a_taken_name_in_another_case_is_a_409_and_creates_nothing(
    client: AsyncClient,
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    client.cookies.clear()
    second = await client.post(
        "/api/auth/register", json={**REGISTER, "username": "ASHA.K", "role": "staff"}
    )
    assert second.status_code == 409
    assert "docket_session" not in client.cookies


async def test_the_stored_password_is_an_argon2_hash(
    client: AsyncClient, connection: AsyncConnection
) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    row = await connection.execute(
        text("SELECT password_hash FROM users WHERE username = 'asha.k'")
    )
    stored = row.scalar_one()
    assert stored.startswith("$argon2id$") and "a-long-phrase-1" not in stored
```

If the file names its fixtures differently from `client` and `connection`, use its names.

- [ ] **Step 2: Run them**

Run (needs `make db` and `make migrate`, against the separate test database in the README): `make test-integration DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docket_it 2>&1 | tail -20`
Expected: pass. If no database is available, report these as "not run".

- [ ] **Step 3: Contract and docs**
  - `api/openapi.yaml`: add `/auth/register` (`operationId: registerUser`, `security: []`, `x-story-ids: [NOTASK-7]`, responses 200 `User`, 409, 422, 429, 500) beside `/auth/login`, and a `RegisterRequest` schema (`username` 3 to 64, `display_name` 1 to 120, `password` 10 to 256 writeOnly, `role` enum staff, verifier, `additionalProperties: false`).
  - `docs/security/permission-matrix.md`: add a row `anonymous | none | register | any | 200 | tests/integration/test_auth_api.py` in the style of the login row, and update the cell count sentence.
  - `docs/security/threat-model-docket.md`: add one threat, "an anonymous caller registers as a verifier and approves applications", rated high, with the accepted-risk note and the mitigations that exist (per-source limit, every decision logged with the actor, Argon2 slots), and the follow-up option of an access code for the verifier role.
  - `docs/security/AUTH.md`: one short section on registration.
  - `docs/adr/0013-open-sign-up-with-a-self-chosen-role.md` from `docs/adr/0000-template.md`: context (two seeded accounts, no way to add people), options (open with role choice, approval, invite link), decision (open with role choice, chosen by the engineer on 2026-10-07 against the recommendation), consequences (anyone can approve applications; revisit before any real data).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_auth_api.py api/openapi.yaml docs
git commit -m "docs(auth): record open sign up and cover it in the contract and tests [NOTASK-7]"
```

---

### Task 4: Sign up screen

**Files:**
- Modify: `frontend/src/features/auth/schemas.ts`, `api.ts`, `hooks.ts`, `notices.ts`, `components/SignInView.tsx`, `frontend/src/app/routes.tsx`
- Create: `frontend/src/features/auth/components/SignUpView.tsx`, `SignUpPage.tsx`, `frontend/src/features/auth/screens/S-01b-sign-up.screen.tsx`, `frontend/src/features/auth/signUp.test.tsx`

**Interfaces:**
- Consumes: `POST /api/auth/register` from Task 2; existing `apiFetch`, `userSchema`, `homeFor`, `resetSitting`, `NoticeBox`.
- Produces: `register(input: RegisterInput): Promise<User>`, `useRegister()`, `registerOutcome(error)`, route `/sign-up`.

- [ ] **Step 1: Write the failing test** (`signUp.test.tsx`, copy the render helpers from `app/auth-flow.test.tsx`)

```tsx
import { createMemoryHistory } from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "@/app/App";
import { fakeSession, userWith } from "@/test/auth";
import { server } from "@/test/msw";
import { createTestQueryClient } from "@/test/render";

function renderSignUp() {
  return render(
    <App
      queryClient={createTestQueryClient()}
      history={createMemoryHistory({ initialEntries: ["/sign-up"] })}
    />,
  );
}

async function fill(user: ReturnType<typeof userEvent.setup>, role: "Staff" | "Verifier") {
  await user.type(await screen.findByLabelText("Your name"), "Asha Kumar");
  await user.type(screen.getByLabelText("Username"), "asha.k");
  await user.type(screen.getByLabelText("Password"), "a-long-phrase-1");
  await user.click(screen.getByRole("radio", { name: new RegExp(role) }));
  await user.click(screen.getByRole("button", { name: "Create account" }));
}

describe("signing up", () => {
  it("opens the review queue for a new verifier", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/register", () => HttpResponse.json(userWith("verifier"))),
      http.get("*/api/auth/me", () => HttpResponse.json(userWith("verifier"))),
    );
    renderSignUp();
    await fill(userEvent.setup(), "Verifier");
    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
  });

  it("says the username is taken on a 409", async () => {
    fakeSession();
    server.use(
      http.post("*/api/auth/register", () =>
        HttpResponse.json(
          { error: { code: "conflict", message: "that username is taken" } },
          { status: 409 },
        ),
      ),
    );
    renderSignUp();
    await fill(userEvent.setup(), "Staff");
    expect(await screen.findByText("That username is taken.")).toBeInTheDocument();
  });

  it("links to sign in and back", async () => {
    fakeSession();
    renderSignUp();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Sign in to Docket" })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Create an account" }));
    expect(await screen.findByRole("heading", { name: "Create your Docket account" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && pnpm vitest run src/features/auth/signUp.test.tsx 2>&1 | tail -20`
Expected: FAIL, no `/sign-up` route

- [ ] **Step 3: Implement**
  - `schemas.ts`: `export interface RegisterInput { username: string; display_name: string; password: string; role: Role }`.
  - `api.ts`: `register(input)` posting to `/api/auth/register` exactly like `login`.
  - `hooks.ts`: `useRegister()` copying `useLogin` with `mutationFn: register`, same `onSuccess` (reset sitting, set `me`), key `authKeys.register()` added to `authKeys`.
  - `notices.ts`: `registerOutcome(error)` returning the same shape as `signInOutcome`: 409 gives title "That username is taken." and body "Choose another."; 422 gives "Check the form." with "Use 3 or more letters, digits, dots, dashes or underscores for the username, and at least 10 characters for the password."; 429 as in sign-in with `blockedFor`; network and fallback as in sign-in.
  - `SignUpView.tsx`: a form like `SignInView` with heading "Create your Docket account"; fields "Your name" (`autoComplete="name"`), "Username" (`autoComplete="username"`), "Password" (`type="password"`, `autoComplete="new-password"`, hint "At least 10 characters"); a `RadioGroup` (from `@/components/ui/radio-group`) named Role with two options, "Staff: import applications, upload documents, export the verified list" and "Verifier: review flagged applications and decide"; a submit button "Create account" (busy label "Creating"); a `Link` to `/sign-in` with text "Sign in". Props `busy`, `blocked`, `notice`, `onSubmit?: (input: RegisterInput) => void`, as in `SignInView`. Role has no default selection and is required.
  - `SignUpPage.tsx`: copy `SignInPage` using `useRegister` and `registerOutcome`, navigating to `homeFor(user.role)` on success.
  - `SignInView.tsx`: under the form add a `Link` to `/sign-up` with text "Create an account".
  - `routes.tsx`: add `signUpRoute` (`path: "/sign-up"`, component `SignUpPage`) beside `signInRoute` and add it to the route tree outside `appRoute`.
  - `S-01b-sign-up.screen.tsx`: a screen module like `S-01-sign-in.screen.tsx` with states loading, empty, `error: conflict`, `error: rate_limited`, `error: unavailable`. If `screens.test.tsx` requires every screen to appear in `docs/design/screens/docket.md`, add a matching entry there.

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend && pnpm vitest run 2>&1 | tail -15`
Expected: all pass, including `screens.test.tsx` and `auth-flow.test.tsx`

- [ ] **Step 5: Gate and commit**

Run: `cd frontend && make check 2>&1 | tail -20`

```bash
git add frontend docs
git commit -m "feat(auth): add the sign up screen [NOTASK-7]"
```

---

### Task 5: Close out

- [ ] **Step 1:** Run `make check` and `cd frontend && make check`; paste the tails into the report.
- [ ] **Step 2:** Run the app (`make db && make migrate && make dev`, then `cd frontend && make dev`) and register one staff and one verifier account in the browser. Check the verifier lands on the Review queue and the staff account on Applications. If the app was not run, report it as "not run".
- [ ] **Step 3:** Write `docs/progress/NOTASK-7.md` with what is done and not done. Do not push; print `git push -u origin docs/NOTASK-7-CompletionDesign` for the engineer.
- [ ] **Step 4:** Report in the AGENTS.md shape: Changed, Verified, Not done, Noticed.

---

## Self-review

- Spec coverage: endpoint, rules, 409, hashing before lookup, limiter, cookies, no schema change, ADR, openapi, matrix, threat model, screen, links, tests. Covered by Tasks 1 to 4. Password change and sign out are already present (sign out exists; password change was not in the final spec and is not planned).
- The spec lists "sign out and change password" only in the conversation, not in the written spec. This plan omits password change on purpose; raise it if wanted.
- Type names match across tasks: `RegistrationLimiter.try_register`, `check_username`, `check_password`, `check_display_name`, `RegisterRequest`, `register`, `useRegister`, `registerOutcome`.
- Branch note: the plan sits on `docs/NOTASK-7-CompletionDesign`. The engineer may prefer a `feature/NOTASK-7-...` branch for the build.
