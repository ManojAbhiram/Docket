"""Create the two demo accounts with generated one-time passwords (threat T-07, ADR-0006).

Run `make seed-accounts`. Each password is random, shown once on the terminal and never written to a
file or a log. Running it again leaves existing accounts alone and prints nothing for them: there is
no reset, so a lost password means a new database or a direct fix by the owner.
"""

import asyncio
import secrets
import sys
from dataclasses import dataclass

from app.core.config import get_settings
from app.db.repositories.auth import SqlAuthStore
from app.db.session import make_engine, make_session_factory
from app.domain.auth import Passwords, Role


@dataclass(frozen=True)
class Account:
    username: str
    display_name: str
    role: Role


ACCOUNTS = (
    Account("staff.demo", "Demo Staff", "staff"),
    Account("verifier.demo", "Demo Verifier", "verifier"),
)


async def seed_accounts(store: SqlAuthStore, passwords: Passwords) -> dict[str, str]:
    """Add the demo accounts that are missing. Returns the password of each one created."""
    issued: dict[str, str] = {}
    for account in ACCOUNTS:
        phrase = secrets.token_urlsafe(18)
        created = await store.create_user(
            account.username, account.display_name, account.role, passwords.hash(phrase)
        )
        if created:
            issued[account.username] = phrase
    return issued


async def _main() -> int:
    settings = get_settings()
    engine = make_engine(settings)
    passwords = Passwords(
        memory_kib=settings.argon2_memory_kib,
        time_cost=settings.argon2_time_cost,
        parallelism=settings.argon2_parallelism,
    )
    try:
        issued = await seed_accounts(SqlAuthStore(make_session_factory(engine)), passwords)
    finally:
        await engine.dispose()
    if not issued:
        sys.stdout.write("Both demo accounts already exist. Nothing issued.\n")
        return 0
    sys.stdout.write("Shown once. Copy them now.\n")
    for username, phrase in issued.items():
        sys.stdout.write(f"  {username}  {phrase}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
