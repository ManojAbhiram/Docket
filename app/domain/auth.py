"""Passwords, session tokens, registration rules and sign-in limiters.

Covers US-00-011, ADR-0006, ADR-0012, ADR-0013. Nothing here touches the database or the request.
A session token is random and only its SHA-256 is stored, so a leaked table cannot be replayed.
The CSRF token is derived from the session token, so it needs no storage and ends with the session.
"""

import hashlib
import hmac
import math
import re
import secrets
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

Role = Literal["staff", "verifier"]

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


_TOKEN_BYTES = 32
_CSRF_LABEL = b"docket-csrf-v1:"


@dataclass(frozen=True)
class UserRecord:
    """A user as sign-in needs it. The hash never leaves the sign-in path."""

    id: UUID
    display_name: str
    role: Role
    password_hash: str
    is_active: bool
    session_version: int


@dataclass(frozen=True)
class SessionUser:
    """Who a live session belongs to, as every other route sees it."""

    id: UUID
    display_name: str
    role: Role


class Passwords:
    """argon2id hashing. The cost is a setting: 64 MiB in production, tiny in tests."""

    def __init__(self, *, memory_kib: int, time_cost: int, parallelism: int) -> None:
        self._hasher = PasswordHasher(
            memory_cost=memory_kib, time_cost=time_cost, parallelism=parallelism
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, stored: str, password: str) -> bool:
        """True only for a match. A stored value that is not a hash never matches."""
        try:
            return self._hasher.verify(stored, password)
        except VerificationError, InvalidHashError:
            return False


def new_token() -> str:
    """A fresh opaque session token: 256 random bits."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    """What the `sessions` table stores in place of the token."""
    return hashlib.sha256(token.encode()).digest()


def csrf_for(token: str) -> str:
    """The anti-forgery token for one session, never equal to anything stored."""
    return hashlib.sha256(_CSRF_LABEL + token.encode()).hexdigest()


def csrf_matches(token: str, offered: str) -> bool:
    return hmac.compare_digest(csrf_for(token), offered)


@dataclass
class _Entry:
    failures: deque[datetime] = field(default_factory=deque)
    locked_until: datetime | None = None


class LoginLimiter:
    """Counts failed sign-ins per account and per source and locks either for a while.

    In memory by design: one API process (ADR-0011), so a restart clears it. Account names are
    folded to lower case, so an unknown name locks exactly like a known one and reveals nothing.
    The number of entries is capped, because the names come from whoever is attacking.
    """

    def __init__(
        self,
        *,
        max_failures: int,
        source_max_failures: int,
        window: timedelta,
        lock: timedelta,
        clock: Callable[[], datetime],
        max_entries: int = 10_000,
    ) -> None:
        self._max = {"account": max_failures, "source": source_max_failures}
        self._window = window
        self._lock = lock
        self._clock = clock
        self._max_entries = max_entries
        self._entries: dict[str, dict[str, _Entry]] = {"account": {}, "source": {}}

    def retry_after(self, username: str, source: str) -> int | None:
        """Seconds until a sign-in may be tried again, or None if it may be tried now."""
        now = self._clock()
        waits = []
        for kind, key in (("account", username.lower()), ("source", source)):
            entry = self._entries[kind].get(key)
            if entry and entry.locked_until and entry.locked_until > now:
                waits.append(math.ceil((entry.locked_until - now).total_seconds()))
        return max(waits) if waits else None

    def record_failure(self, username: str, source: str) -> None:
        for kind, key in (("account", username.lower()), ("source", source)):
            self._fail(kind, key)

    def record_success(self, username: str) -> None:
        self._entries["account"].pop(username.lower(), None)

    def size(self) -> int:
        return sum(len(entries) for entries in self._entries.values())

    def _fail(self, kind: str, key: str) -> None:
        now = self._clock()
        entries = self._entries[kind]
        entry = entries.pop(key, None) or _Entry()
        entries[key] = entry  # most recently used goes last, so eviction drops the oldest
        while entry.failures and now - entry.failures[0] > self._window:
            entry.failures.popleft()
        entry.failures.append(now)
        if len(entry.failures) >= self._max[kind]:
            entry.locked_until = now + self._lock
            entry.failures.clear()
        while len(entries) > self._max_entries:
            del entries[next(iter(entries))]


class RegistrationLimiter:
    """Allows a few registrations per source per window.

    In memory, like LoginLimiter (ADR-0011). Only allowed attempts are counted, so a flood of
    refused ones does not extend its own wait. The number of sources kept is capped, because the
    sources come from whoever is attacking.
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
        """None if this attempt may go ahead (and is counted), else seconds to wait."""
        now = self._clock()
        attempts = self._attempts.pop(source, None) or deque()
        self._attempts[source] = attempts  # most recently used goes last
        while attempts and now - attempts[0] > self._window:
            attempts.popleft()
        wait: int | None = None
        if len(attempts) >= self._max:
            oldest = attempts[0] if attempts else now
            wait = max(1, math.ceil((oldest + self._window - now).total_seconds()))
        else:
            attempts.append(now)
        while len(self._attempts) > self._max_entries:
            del self._attempts[next(iter(self._attempts))]
        return wait

    def size(self) -> int:
        return len(self._attempts)
