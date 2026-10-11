"""Load the synthetic demo through an existing local staff session."""

import argparse
import asyncio
import getpass
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from httpx import AsyncClient, HTTPError, Response
from pydantic import BaseModel, ValidationError

from app.api.applications.schemas import ApplicationListOut, ApplicationOut
from app.api.auth.schemas import UserOut
from app.api.documents.schemas import DocumentOut
from app.api.imports.schemas import ImportResultOut
from seed.dataset import Application, Dataset, applications_csv, build_dataset


@dataclass(frozen=True)
class LoadResult:
    applications_created: int
    applications_existing: int
    documents_created: int
    documents_existing: int


class LoadError(RuntimeError):
    """A safe loader failure that never includes credentials, cookies or response bodies."""


def local_url(base_url: str) -> str:
    """Validate the destination before asking for or transmitting credentials."""
    try:
        url = urlparse(base_url)
        port = url.port
    except ValueError:
        raise LoadError("seed-load requires a valid local API URL") from None
    if (
        url.scheme not in {"http", "https"}
        or url.hostname not in {"localhost", "127.0.0.1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
        or port == 0
    ):
        raise LoadError("seed-load requires an explicit local API at localhost or 127.0.0.1")
    return base_url.rstrip("/")


def response_model[Model: BaseModel](
    response: Response, schema: type[Model], statuses: tuple[int, ...]
) -> Model:
    """Accept only known statuses and schema-valid bodies without including server output."""
    if response.status_code not in statuses:
        raise LoadError(f"local API request failed: HTTP {response.status_code}")
    try:
        return schema.model_validate_json(response.content)
    except ValidationError:
        raise LoadError("local API returned an invalid response") from None


def agrees(application: ApplicationOut, expected: Application) -> bool:
    """An existing seed reference must still hold every value submitted in the CSV."""
    return (
        application.application_ref,
        application.full_name,
        application.father_name,
        application.date_of_birth,
        application.board,
        application.roll_number,
        application.marks,
        application.category,
    ) == (
        expected.application_id,
        expected.name,
        expected.father_name,
        expected.dob,
        expected.board,
        expected.roll_number,
        expected.marks,
        expected.category,
    )


async def application_ids(client: AsyncClient, dataset: Dataset) -> dict[str, str]:
    """Find the imported seed records across all pages and refuse incompatible existing records."""
    expected = {application.application_id: application for application in dataset.applications}
    identifiers: dict[str, str] = {}
    cursor: str | None = None
    while True:
        params = {"limit": "100"}
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get("/api/applications", params=params)
        page = response_model(response, ApplicationListOut, (200,))
        for application in page.data:
            if application.application_ref not in expected:
                continue
            if not agrees(application, expected[application.application_ref]):
                raise LoadError("an existing seed application differs from the synthetic dataset")
            identifiers[application.application_ref] = str(application.id)
        if not page.page.has_more:
            break
        if page.page.next_cursor is None or page.page.next_cursor == cursor:
            raise LoadError("local API returned invalid application pagination")
        cursor = page.page.next_cursor
    if identifiers.keys() != expected.keys():
        raise LoadError("not every synthetic application is available after import")
    return identifiers


async def authenticated_load(
    base_url: str, username: str, password: str, png_dir: Path
) -> LoadResult:
    """Sign into the explicit local API with an existing staff account."""
    base_url = local_url(base_url)
    async with AsyncClient(
        base_url=base_url, timeout=180, follow_redirects=False, trust_env=False
    ) as client:
        response = await client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        if response_model(response, UserOut, (200,)).role != "staff":
            raise LoadError("the seed loader requires a staff account")
        token = client.cookies.get("docket_csrf")
        if token is None:
            raise LoadError("staff sign-in did not return a CSRF cookie")
        return await load(
            client, build_dataset(), png_dir, {"Origin": base_url, "X-CSRF-Token": token}
        )


async def load(
    client: AsyncClient, dataset: Dataset, png_dir: Path, headers: dict[str, str]
) -> LoadResult:
    """Import and upload the deterministic synthetic dataset through authenticated routes."""
    fixtures = [
        (document, await asyncio.to_thread((png_dir / document.file_name).read_bytes))
        for document in dataset.documents
    ]
    response = await client.post(
        "/api/imports",
        files={
            "file": ("synthetic-applications.csv", applications_csv(dataset).encode(), "text/csv")
        },
        headers=headers,
    )
    imported = response_model(response, ImportResultOut, (201,))
    if imported.rows_read != len(dataset.applications) or any(
        error.reason_code != "duplicate_application_ref" for error in imported.errors
    ):
        raise LoadError("the synthetic application import rejected a nonduplicate row")
    identifiers = await application_ids(client, dataset)
    created = 0
    existing = 0
    for document, content in fixtures:
        response = await client.post(
            f"/api/applications/{identifiers[document.application_id]}/documents",
            files={"file": (document.file_name, content, "image/png")},
            data={"mode": "free"},
            headers=headers,
        )
        record = response_model(response, DocumentOut, (200, 202))
        if (
            str(record.application_id) != identifiers[document.application_id]
            or record.requested_mode != "free"
        ):
            raise LoadError(
                "local API stored a synthetic document against an unexpected application or mode"
            )
        created += response.status_code == 202
        existing += response.status_code == 200
    return LoadResult(imported.rows_created, imported.rows_rejected, created, existing)


def main(argv: Sequence[str] | None = None) -> int:
    """Authenticate against a local API and queue its synthetic seed documents."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--username", required=True)
    parser.add_argument("--png-dir", type=Path, default=Path("data/seed/png"))
    args = parser.parse_args(argv)
    try:
        base_url = local_url(args.base_url)
    except LoadError as exc:
        parser.error(str(exc))
    password = getpass.getpass("Staff password: ")
    try:
        result = asyncio.run(authenticated_load(base_url, args.username, password, args.png_dir))
    except LoadError as exc:
        parser.exit(1, f"seed-load: {exc}\n")
    except HTTPError:
        parser.exit(1, "seed-load: local API request failed\n")
    except OSError:
        parser.exit(1, "seed-load: synthetic PNG fixtures could not be read\n")
    sys.stdout.write(json.dumps(asdict(result), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
