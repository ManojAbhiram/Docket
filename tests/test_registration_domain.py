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

    assert wait is not None
    assert 0 < wait <= 3600


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


def test_limiter_with_max_per_source_zero_returns_window_seconds() -> None:
    clock = _Clock()
    limiter = RegistrationLimiter(
        max_per_source=0, window=timedelta(hours=1), clock=clock, max_entries=10_000
    )
    wait = limiter.try_register("1.2.3.4")
    assert wait == 3600
    # Verify it doesn't raise IndexError
    wait2 = limiter.try_register("1.2.3.4")
    assert wait2 == 3600
