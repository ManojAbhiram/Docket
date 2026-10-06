"""What every protected route depends on: the signed-in user, the role gate and the CSRF check.

A route is protected by adding `current_user`, `require_role(...)` and, for anything that changes
data, `verify_csrf` to its dependencies. The `docket_session` cookie holds an opaque token; only its
hash is stored (ADR-0006). The CSRF token is derived from that same cookie and sent back in the
`X-CSRF-Token` header, which a page on another site cannot read.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.db.repositories.auth import SqlAuthStore
from app.domain.auth import Role, SessionUser, csrf_matches, hash_token

SESSION_COOKIE = "docket_session"
CSRF_COOKIE = "docket_csrf"
CSRF_HEADER = "X-CSRF-Token"


def get_settings_from_app(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Callable[[], datetime]:
    clock: Callable[[], datetime] = request.app.state.clock
    return clock


def get_auth_store(request: Request) -> SqlAuthStore:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return SqlAuthStore(factory)


async def current_user(
    request: Request,
    store: Annotated[SqlAuthStore, Depends(get_auth_store)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
    clock: Annotated[Callable[[], datetime], Depends(get_clock)],
) -> SessionUser:
    """The user of the live session in the cookie, or 401. The reason is never given."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise UnauthorizedError("sign in to continue")
    user = await store.resolve(
        hash_token(token),
        now=clock(),
        idle=timedelta(minutes=settings.session_idle_minutes),
    )
    if user is None:
        raise UnauthorizedError("sign in to continue")
    return user


def require_role(*roles: Role) -> Callable[[SessionUser], Awaitable[SessionUser]]:
    """A dependency that lets only the named roles through. Anyone else gets 403."""

    async def check(user: Annotated[SessionUser, Depends(current_user)]) -> SessionUser:
        if user.role not in roles:
            raise ForbiddenError("this role may not do that")
        return user

    return check


async def verify_csrf(
    request: Request, settings: Annotated[Settings, Depends(get_settings_from_app)]
) -> None:
    """Refuse a state-changing request from another origin or without the matching token."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.origins:
        raise ForbiddenError("request origin is not allowed")
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise UnauthorizedError("sign in to continue")
    offered = request.headers.get(CSRF_HEADER, "")
    if not csrf_matches(token, offered):
        raise ForbiddenError("anti-forgery token missing or wrong")
