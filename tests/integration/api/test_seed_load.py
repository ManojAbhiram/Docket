"""The deterministic demo dataset loads through authenticated APIs and can be loaded again."""

import getpass
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.api.auth.schemas import UserOut
from seed import load as seed_load
from seed.dataset import applications_csv, build_dataset
from tests.integration.helpers import csrf_header, seed_user, sign_in

pytestmark = pytest.mark.integration


@pytest.fixture
def seed_limits(api_app: FastAPI) -> None:
    api_app.state.settings = api_app.state.settings.model_copy(
        update={"import_max_bytes": 5_000_000, "upload_max_bytes": 8 * 1024 * 1024}
    )


async def test_load_creates_twenty_applications_and_thirty_free_documents(
    api: AsyncClient, connection: AsyncConnection, seed_limits: None
) -> None:
    # NOTASK-17: generated fixtures must also be loadable into the running application's API.
    await seed_user(connection, "staff.seed", "staff")
    await sign_in(api, "staff.seed")

    result = await seed_load.load(api, build_dataset(), Path("data/seed/png"), csrf_header(api))

    assert result.applications_created == 20
    assert result.documents_created == 30
    assert (
        await connection.execute(
            text("SELECT count(*) FROM applications WHERE application_ref LIKE 'SYN-APP-%'")
        )
    ).scalar_one() == 20
    assert (
        await connection.execute(
            text(
                "SELECT count(*) FROM documents d JOIN applications a "
                "ON a.id = d.application_id WHERE a.application_ref LIKE 'SYN-APP-%'"
            )
        )
    ).scalar_one() == 30
    assert (
        await connection.execute(
            text(
                "SELECT DISTINCT d.requested_mode FROM documents d JOIN applications a "
                "ON a.id = d.application_id WHERE a.application_ref LIKE 'SYN-APP-%'"
            )
        )
    ).scalars().all() == ["free"]


async def test_loading_twice_reuses_the_same_applications_and_documents(
    api: AsyncClient, connection: AsyncConnection, seed_limits: None
) -> None:
    await seed_user(connection, "staff.seed", "staff")
    await sign_in(api, "staff.seed")
    await seed_load.load(api, build_dataset(), Path("data/seed/png"), csrf_header(api))

    dataset = build_dataset()
    other = replace(
        dataset,
        applications=tuple(
            replace(dataset.applications[0], application_id=f"SYN-PAGE-{index:03d}")
            for index in range(100)
        ),
    )
    imported = await api.post(
        "/api/imports",
        files={"file": ("other.csv", applications_csv(other).encode(), "text/csv")},
        headers=csrf_header(api),
    )
    assert imported.status_code == 201
    await connection.execute(
        text(
            "UPDATE applications SET updated_at = now() - interval '1 day' "
            "WHERE application_ref LIKE 'SYN-APP-%'"
        )
    )

    again = await seed_load.load(api, build_dataset(), Path("data/seed/png"), csrf_header(api))

    assert again.applications_created == 0
    assert again.documents_created == 0
    assert again.applications_existing == 20
    assert again.documents_existing == 30
    assert (
        await connection.execute(
            text("SELECT count(*) FROM applications WHERE application_ref LIKE 'SYN-APP-%'")
        )
    ).scalar_one() == 20
    assert (
        await connection.execute(
            text(
                "SELECT count(*) FROM documents d JOIN applications a "
                "ON a.id = d.application_id WHERE a.application_ref LIKE 'SYN-APP-%'"
            )
        )
    ).scalar_one() == 30


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid",
        "http://localhost.example.invalid",
        "http://user:secret@localhost",
        "http://localhost:badport",
    ],
)
def test_cli_rejects_an_invalid_destination_before_prompting_for_a_password(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    def refuse(_prompt: str) -> str:
        pytest.fail("a remote API must be refused before requesting credentials")

    monkeypatch.setattr(getpass, "getpass", refuse)

    with pytest.raises(SystemExit, match="2"):
        seed_load.main(["--base-url", url, "--username", "staff.demo"])


async def test_authenticated_loader_also_refuses_a_remote_destination() -> None:
    with pytest.raises(seed_load.LoadError, match="local API"):
        await seed_load.authenticated_load(
            "https://example.invalid", "staff.seed", "synthetic-password", Path("data/seed/png")
        )


def test_invalid_api_response_is_reported_without_its_body() -> None:
    response = Response(200, json={"password": "synthetic-value-must-not-be-printed"})

    with pytest.raises(seed_load.LoadError) as raised:
        seed_load.response_model(response, UserOut, (200,))

    assert str(raised.value) == "local API returned an invalid response"


async def test_incompatible_existing_seed_values_stop_before_uploading_documents(
    api: AsyncClient, connection: AsyncConnection, seed_limits: None
) -> None:
    await seed_user(connection, "staff.seed", "staff")
    await sign_in(api, "staff.seed")
    await api.post(
        "/api/imports",
        files={"file": ("seed.csv", applications_csv(build_dataset()).encode(), "text/csv")},
        headers=csrf_header(api),
    )
    await connection.execute(
        text(
            "UPDATE applications SET father_name = 'Synthetic wrong parent' "
            "WHERE application_ref = 'SYN-APP-001'"
        )
    )

    with pytest.raises(seed_load.LoadError, match="differs from the synthetic dataset"):
        await seed_load.load(api, build_dataset(), Path("data/seed/png"), csrf_header(api))

    assert (
        await connection.execute(
            text(
                "SELECT count(*) FROM documents d JOIN applications a "
                "ON a.id = d.application_id WHERE a.application_ref LIKE 'SYN-APP-%'"
            )
        )
    ).scalar_one() == 0
