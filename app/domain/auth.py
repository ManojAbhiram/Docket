"""Passwords, session tokens and the login limiter (US-00-011, ADR-0006, ADR-0012).

Nothing here touches the database or the request. A session token is random and only its SHA-256 is
stored, so a leaked table cannot be replayed. The CSRF token is derived from the session token, so
it needs no storage and ends with the session.
"""

import hashlib
import hmac
import math
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
