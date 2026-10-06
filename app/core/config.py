"""Process configuration from the environment.

Construction fails fast and names every invalid variable at once. Secrets
have no defaults. `get_settings` is the one module-level singleton.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_EXAMPLE_PASSWORDS = frozenset({None, "", "postgres", "password", "changeme"})

Env = Literal["development", "test", "production"]
LogLevel = Literal["debug", "info", "warning", "error"]
LogFormat = Literal["json", "console"]


class Settings(BaseSettings):
    """Validated process configuration, read from the environment and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Docket"
    env: Env = "development"
    port: int = 8080
    log_level: LogLevel = "info"
    log_format: LogFormat = "json"
    database_url: PostgresDsn = Field(repr=False)
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_echo: bool = False
    readiness_timeout_seconds: float = Field(default=2.0, gt=0)
    gateway_engine: str = "recorded"
    gateway_call_cap: int = Field(default=1000, ge=1)
    gateway_recording: Path | None = None
    # The document worker runs inside the API process (ADR-0011). Off unless asked for.
    worker_enabled: bool = False
    worker_idle_seconds: float = Field(default=2.0, gt=0)
    sweep_interval_seconds: float = Field(default=60.0, gt=0)
    read_timeout_seconds: float = Field(default=120.0, gt=0)
    engine_recycle_after: int = Field(default=500, ge=1)
    review_confidence_cutoff: float = Field(default=0.9804, ge=0, le=1)
    name_match_threshold: float = Field(default=0.85, ge=0, le=1)
    import_max_bytes: int = Field(default=5_000_000, ge=1_000)
    import_max_rows: int = Field(default=20_000, ge=1)
    upload_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1_000)
    # Sessions and sign-in (ADR-0006, ADR-0012). Lifetimes are assumptions until the owner confirms.
    session_cookie_secure: bool = True
    session_idle_minutes: int = Field(default=30, ge=1)
    session_absolute_hours: int = Field(default=8, ge=1)
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    login_max_failures: int = Field(default=5, ge=1)
    login_source_max_failures: int = Field(default=20, ge=1)
    login_window_minutes: int = Field(default=15, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)
    login_hash_concurrency: int = Field(default=2, ge=1)
    argon2_memory_kib: int = Field(default=65536, ge=8)
    argon2_time_cost: int = Field(default=3, ge=1)
    argon2_parallelism: int = Field(default=1, ge=1)

    @property
    def origins(self) -> frozenset[str]:
        """The origins a state-changing request may come from."""
        return frozenset(o.strip() for o in self.allowed_origins.split(",") if o.strip())

    @model_validator(mode="after")
    def _production_has_a_real_database_password(self) -> Self:
        """The example password is for a laptop. Production refuses it."""
        password = self.database_url.hosts()[0].get("password")
        if self.env == "production" and password in _EXAMPLE_PASSWORDS:
            msg = "production refuses an example database password"
            raise ValueError(msg)
        if self.env == "production" and not self.session_cookie_secure:
            msg = "production requires SESSION_COOKIE_SECURE=true"
            raise ValueError(msg)
        return self

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: PostgresDsn) -> PostgresDsn:
        """The whole stack is async; a sync driver here would block the loop."""
        if value.scheme != "postgresql+asyncpg":
            msg = f"DATABASE_URL must use postgresql+asyncpg://, got {value.scheme}://"
            raise ValueError(msg)
        return value


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()
