"""Configuration and secrets from the environment (`.claude/rules/security.md`).

Secrets have no defaults, never print, and the example file documents every variable with a
placeholder. Tests that need the new settings fail until `app/core/config.py` has them.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

URL = "postgresql+asyncpg://app:{password}@localhost:5432/docket"


def make(**overrides: object) -> Settings:
    base: dict[str, object] = {"env": "test", "database_url": URL.format(password="s3cretvalue")}
    return Settings.model_validate(base | overrides)


def test_the_printed_settings_never_show_the_database_password() -> None:
    settings = make()

    assert "s3cretvalue" not in repr(settings)
    assert "s3cretvalue" not in str(settings)


@pytest.mark.parametrize("password", ["postgres", "password", "changeme"])
def test_production_refuses_an_example_database_password(password: str) -> None:
    with pytest.raises(ValidationError, match="production"):
        make(env="production", database_url=URL.format(password=password))


def test_production_accepts_a_database_password_that_is_not_an_example() -> None:
    assert make(env="production", database_url=URL.format(password="x9Qv-long-secret")).env == (
        "production"
    )


def test_production_refuses_a_session_cookie_that_is_not_secure() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        make(
            env="production",
            database_url=URL.format(password="x9Qv-long-secret"),
            session_cookie_secure=False,
        )


def test_the_session_cookie_is_secure_unless_a_developer_turns_it_off() -> None:
    assert make().session_cookie_secure is True
    assert make(session_cookie_secure=False).session_cookie_secure is False


@pytest.mark.parametrize("env", ["development", "test"])
def test_development_and_test_may_use_the_example_password(env: str) -> None:
    assert make(env=env, database_url=URL.format(password="postgres")).env == env


def test_a_missing_database_url_is_refused_and_named() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        Settings.model_validate({"env": "test"})


def test_every_setting_is_documented_in_the_example_file() -> None:
    lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
    documented = {line.split("=")[0].strip() for line in lines if "=" in line and line[0] != "#"}

    assert {name.upper() for name in Settings.model_fields} <= documented


def test_the_review_confidence_cutoff_defaults_to_the_provisional_value_in_adr_0005() -> None:
    assert make().review_confidence_cutoff == 0.9804


@pytest.mark.parametrize("cutoff", [-0.1, 1.1])
def test_a_confidence_cutoff_outside_zero_to_one_is_refused(cutoff: float) -> None:
    with pytest.raises(ValidationError):
        make(review_confidence_cutoff=cutoff)


def test_the_call_cap_must_be_at_least_one() -> None:
    assert make().gateway_call_cap >= 1
    with pytest.raises(ValidationError):
        make(gateway_call_cap=0)


def test_the_default_engine_is_the_recorded_one_so_nothing_reaches_a_model_by_accident() -> None:
    assert make().gateway_engine == "recorded"
