"""Sign in, sign out and who am I (api/openapi.yaml: /auth/login, /auth/logout, /auth/me)."""

import asyncio
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response

from app.api.auth.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    current_user,
    get_auth_store,
    get_settings_from_app,
    verify_csrf,
)
from app.api.auth.schemas import LoginRequest, UserOut
from app.core.config import Settings
from app.core.errors import ErrorEnvelope, TooManyAttemptsError, UnauthorizedError
from app.db.repositories.auth import SqlAuthStore
from app.domain.auth import LoginLimiter, Passwords, SessionUser, csrf_for, hash_token, new_token

router = APIRouter(prefix="/auth", tags=["auth"])

_ERRORS: dict[int | str, dict[str, Any]] = {401: {"model": ErrorEnvelope}}


@router.post(
    "/login",
    response_model=UserOut,
    responses={**_ERRORS, 429: {"model": ErrorEnvelope}},
)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    store: Annotated[SqlAuthStore, Depends(get_auth_store)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> UserOut:
    """Check the password, start a session and set its two cookies.

    An unknown name, a wrong password and a deactivated account all answer the same 401 and all
    cost one password hash, so neither the body nor the timing says which one it was.
    """
    state = request.app.state
    limiter: LoginLimiter = state.login_limiter
    passwords: Passwords = state.passwords
    source = request.client.host if request.client else "unknown"
    wait = limiter.retry_after(body.username, source)
    if wait is not None:
        raise TooManyAttemptsError(
            "too many failed sign-ins, try again later", headers={"Retry-After": str(wait)}
        )
    user = await store.find_user(body.username)
    usable = user is not None and user.is_active
    stored = user.password_hash if user is not None and usable else state.dummy_hash
    async with state.hash_slots:
        matched = await asyncio.to_thread(passwords.verify, stored, body.password)
    if user is None or not usable or not matched:
        limiter.record_failure(body.username, source)
        raise UnauthorizedError("username or password is wrong")
    limiter.record_success(body.username)
    token = new_token()
    now = state.clock()
    lifetime = timedelta(hours=settings.session_absolute_hours)
    await store.start_session(user, hash_token(token), now=now, expires_at=now + lifetime)
    _set_cookie(response, SESSION_COOKIE, token, settings, http_only=True)
    _set_cookie(response, CSRF_COOKIE, csrf_for(token), settings, http_only=False)
    return UserOut(id=user.id, display_name=user.display_name, role=user.role)


@router.post(
    "/logout",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(verify_csrf)],
    responses={**_ERRORS, 403: {"model": ErrorEnvelope}},
)
async def logout(
    request: Request,
    _: Annotated[SessionUser, Depends(current_user)],
    store: Annotated[SqlAuthStore, Depends(get_auth_store)],
) -> Response:
    """End this session on the server and clear both cookies."""
    token = request.cookies[SESSION_COOKIE]
    await store.revoke(hash_token(token), now=request.app.state.clock())
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserOut, responses=_ERRORS)
async def me(user: Annotated[SessionUser, Depends(current_user)]) -> UserOut:
    """Who this session belongs to."""
    return UserOut(id=user.id, display_name=user.display_name, role=user.role)


def _set_cookie(
    response: Response, name: str, value: str, settings: Settings, *, http_only: bool
) -> None:
    response.set_cookie(
        name,
        value,
        max_age=settings.session_absolute_hours * 3600,
        path="/",
        httponly=http_only,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
