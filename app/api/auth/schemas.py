"""Request and response bodies for sign-in (api/openapi.yaml: LoginRequest, User)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.auth import Role


class LoginRequest(BaseModel):
    """Both fields are bounded before any hashing happens."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    """Who is signed in. No hash, no username, no version."""

    id: UUID
    display_name: str
    role: Role
