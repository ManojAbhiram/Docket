"""Users and sessions in Postgres (US-00-011, ADR-0006). Sign-in SQL lives here only.

A session is live while it is not revoked, has not passed its absolute end, was seen within the idle
window, and its user is active and still on the `session_version` the session was made with. One
statement checks all of that and moves `last_seen_at`, so a request costs one round trip.
"""

from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.auth import Role, SessionUser, UserRecord

_FIND_USER = text(
    "SELECT id, display_name, role::text, password_hash, is_active, session_version "
    "FROM users WHERE lower(username) = lower(:username)"
)
_START_SESSION = text(
    "INSERT INTO sessions (user_id, token_hash, session_version, created_at, last_seen_at, "
    "expires_at) VALUES (:user_id, :token_hash, :version, :now, :now, :expires_at)"
)
_MARK_LOGIN = text("UPDATE users SET last_login_at = :now, updated_at = :now WHERE id = :id")
_RESOLVE = text(
    "UPDATE sessions s SET last_seen_at = :now FROM users u "
    "WHERE u.id = s.user_id AND s.token_hash = :token_hash AND s.revoked_at IS NULL "
    "AND s.expires_at > :now AND s.last_seen_at > :idle_cutoff "
    "AND u.is_active AND u.session_version = s.session_version "
    "RETURNING u.id, u.display_name, u.role::text"
)
_REVOKE = text(
    "UPDATE sessions SET revoked_at = :now WHERE token_hash = :token_hash AND revoked_at IS NULL"
)
_CREATE_USER = text(
    "INSERT INTO users (username, display_name, role, password_hash) "
    "VALUES (:username, :display_name, CAST(:role AS user_role), :password_hash) "
    "ON CONFLICT DO NOTHING RETURNING id"
)


class SqlAuthStore:
    """The users and sessions tables, behind the few questions sign-in asks."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def find_user(self, username: str) -> UserRecord | None:
        async with self._factory() as session:
            row = (await session.execute(_FIND_USER, {"username": username})).first()
        if row is None:
            return None
        return UserRecord(
            id=row[0],
            display_name=row[1],
            role=cast("Role", row[2]),
            password_hash=row[3],
            is_active=row[4],
            session_version=row[5],
        )

    async def start_session(
        self, user: UserRecord, token_hash: bytes, *, now: datetime, expires_at: datetime
    ) -> None:
        async with self._factory.begin() as session:
            await session.execute(
                _START_SESSION,
                {
                    "user_id": user.id,
                    "token_hash": token_hash,
                    "version": user.session_version,
                    "now": now,
                    "expires_at": expires_at,
                },
            )
            await session.execute(_MARK_LOGIN, {"id": user.id, "now": now})

    async def resolve(
        self, token_hash: bytes, *, now: datetime, idle: timedelta
    ) -> SessionUser | None:
        """The user of a live session, whose idle clock restarts, or None."""
        async with self._factory.begin() as session:
            row = (
                await session.execute(
                    _RESOLVE, {"token_hash": token_hash, "now": now, "idle_cutoff": now - idle}
                )
            ).first()
        if row is None:
            return None
        return SessionUser(id=row[0], display_name=row[1], role=cast("Role", row[2]))

    async def revoke(self, token_hash: bytes, *, now: datetime) -> None:
        async with self._factory.begin() as session:
            await session.execute(_REVOKE, {"token_hash": token_hash, "now": now})

    async def create_user(
        self, username: str, display_name: str, role: Role, password_hash: str
    ) -> bool:
        """Add an account. False when the name is taken, ignoring case, and nothing changed."""
        async with self._factory.begin() as session:
            created = (
                await session.execute(
                    _CREATE_USER,
                    {
                        "username": username,
                        "display_name": display_name,
                        "role": role,
                        "password_hash": password_hash,
                    },
                )
            ).first()
        return created is not None
