"""Request and response bodies for sign-in and sign up (api/openapi.yaml)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.auth import Role, check_display_name, check_password, check_username


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
    def _password(self) -> RegisterRequest:
        check_password(self.password, self.username)
        return self
