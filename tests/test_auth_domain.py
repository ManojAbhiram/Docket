"""Passwords, session tokens and the login limiter (US-00-011, threats T-01, T-05, T-06)."""

from datetime import UTC, datetime, timedelta

from app.domain.auth import LoginLimiter, Passwords, csrf_for, hash_token, new_token

START = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: int) -> None:
        self.now += timedelta(**delta)


def small_passwords() -> Passwords:
    return Passwords(memory_kib=8, time_cost=1, parallelism=1)


def test_a_password_verifies_against_its_own_hash_and_not_another() -> None:
    passwords = small_passwords()
    stored = passwords.hash("correct horse")

    assert passwords.verify(stored, "correct horse") is True
    assert passwords.verify(stored, "wrong horse") is False


def test_the_hash_is_argon2id_salted_and_never_holds_the_password() -> None:
    passwords = small_passwords()

    first, second = passwords.hash("correct horse"), passwords.hash("correct horse")

    assert first.startswith("$argon2id$")
    assert first != second
    assert "correct horse" not in first


def test_a_malformed_stored_hash_fails_closed() -> None:
    assert small_passwords().verify("not a hash", "anything") is False


def test_session_tokens_are_unique_and_long_enough_for_256_bits() -> None:
    tokens = {new_token() for _ in range(50)}

    assert len(tokens) == 50
    assert all(len(token) >= 43 for token in tokens)


def test_a_token_hash_is_a_stable_sha256_that_is_not_the_token() -> None:
    token = new_token()

    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 32
    assert token.encode() != hash_token(token)


def test_the_csrf_token_follows_the_session_token_and_reveals_neither_hash() -> None:
    first, second = new_token(), new_token()

    assert csrf_for(first) == csrf_for(first)
    assert csrf_for(first) != csrf_for(second)
    assert csrf_for(first) != first
    assert hash_token(first).hex() not in csrf_for(first)


def make_limiter(clock: Clock) -> LoginLimiter:
    return LoginLimiter(
        max_failures=5,
        source_max_failures=20,
        window=timedelta(minutes=15),
        lock=timedelta(minutes=15),
        clock=clock,
    )


def test_four_failures_do_not_lock_an_account() -> None:
    limiter = make_limiter(Clock())

    for _ in range(4):
        limiter.record_failure("staff.demo", "10.0.0.1")

    assert limiter.retry_after("staff.demo", "10.0.0.1") is None


def test_the_fifth_failure_locks_the_account_for_fifteen_minutes() -> None:
    limiter = make_limiter(Clock())

    for _ in range(5):
        limiter.record_failure("staff.demo", "10.0.0.1")

    assert limiter.retry_after("staff.demo", "10.0.0.1") == 900


def test_a_locked_account_opens_again_when_the_lock_has_passed() -> None:
    clock = Clock()
    limiter = make_limiter(clock)
    for _ in range(5):
        limiter.record_failure("staff.demo", "10.0.0.1")

    clock.advance(minutes=15, seconds=1)

    assert limiter.retry_after("staff.demo", "10.0.0.1") is None


def test_failures_older_than_the_window_are_forgotten() -> None:
    clock = Clock()
    limiter = make_limiter(clock)
    for _ in range(4):
        limiter.record_failure("staff.demo", "10.0.0.1")
    clock.advance(minutes=16)

    limiter.record_failure("staff.demo", "10.0.0.1")

    assert limiter.retry_after("staff.demo", "10.0.0.1") is None


def test_a_successful_sign_in_clears_the_failures_of_that_account() -> None:
    limiter = make_limiter(Clock())
    for _ in range(4):
        limiter.record_failure("staff.demo", "10.0.0.1")

    limiter.record_success("staff.demo")
    limiter.record_failure("staff.demo", "10.0.0.1")

    assert limiter.retry_after("staff.demo", "10.0.0.1") is None


def test_an_unknown_name_locks_exactly_like_a_known_one_and_case_does_not_matter() -> None:
    limiter = make_limiter(Clock())

    for name in ("Nobody.Here", "nobody.here", "NOBODY.HERE", "nobody.here", "Nobody.here"):
        limiter.record_failure(name, "10.0.0.1")

    assert limiter.retry_after("nobody.here", "10.0.0.2") == 900


def test_twenty_failures_from_one_source_lock_that_source_across_accounts() -> None:
    limiter = make_limiter(Clock())

    for number in range(20):
        limiter.record_failure(f"user{number}", "10.0.0.9")

    assert limiter.retry_after("fresh.account", "10.0.0.9") == 900
    assert limiter.retry_after("fresh.account", "10.0.0.8") is None


def test_the_limiter_keeps_a_bounded_number_of_entries() -> None:
    limiter = LoginLimiter(
        max_failures=5,
        source_max_failures=20,
        window=timedelta(minutes=15),
        lock=timedelta(minutes=15),
        clock=Clock(),
        max_entries=100,
    )

    for number in range(500):
        limiter.record_failure(f"user{number}", f"10.0.{number // 250}.{number % 250}")

    assert limiter.size() <= 200
