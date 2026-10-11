"""Exercise an isolated local API with real OCR, maximum size uploads and concurrent sign-ins.

The caller starts the local container and records its cgroup peak and OOM events separately.
This driver uses synthetic data only and never prints credentials or session cookies.
"""

import argparse
import asyncio
import dataclasses
import json
import secrets
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np

from app.api.applications.schemas import ApplicationDetailOut, ApplicationListOut
from app.api.documents.schemas import DocumentOut
from app.api.imports.schemas import ImportResultOut
from seed.dataset import Dataset, applications_csv, build_dataset


def maximum_png(index: int) -> bytes:
    """Draw a distinct, compressed 25 megapixel synthetic upload on the host."""
    pixels = np.full((5000, 5000, 3), 255, dtype=np.uint8)
    cv2.putText(
        pixels,
        f"Synthetic maximum page {index}",
        (100, 500),
        cv2.FONT_HERSHEY_SIMPLEX,
        5,
        (0, 0, 0),
        8,
    )
    ok, encoded = cv2.imencode(".png", pixels)
    if not ok:
        raise RuntimeError("could not encode synthetic maximum page")
    return encoded.tobytes()


def require_status(response: httpx.Response, expected: tuple[int, ...]) -> None:
    """Fail without including a response body or request credentials."""
    if response.status_code not in expected:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path}: "
            f"status {response.status_code}, expected {expected}"
        )


async def upload(
    client: httpx.AsyncClient,
    application_id: str,
    name: str,
    content: bytes,
    headers: dict[str, str],
) -> str:
    """Upload a synthetic PNG and return its document id."""
    response = await client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": (name, content, "image/png")},
        headers=headers,
    )
    require_status(response, (200, 202))
    return str(DocumentOut.model_validate_json(response.content).id)


async def sign_in(base_url: str, username: str, password: str) -> int:
    """Use a separate session for a simultaneous real password verification."""
    async with httpx.AsyncClient(base_url=base_url, timeout=180) as client:
        response = await client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        require_status(response, (200,))
        return response.status_code


async def await_read(
    client: httpx.AsyncClient,
    applications: set[str],
    document_ids: set[str],
    deadline_seconds: float,
) -> dict[str, str]:
    """Wait for all uploaded documents to complete through the real RapidOCR worker."""
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        observed: dict[str, str] = {}
        for application_id in applications:
            response = await client.get(f"/api/applications/{application_id}")
            require_status(response, (200,))
            detail = ApplicationDetailOut.model_validate_json(response.content)
            for document in detail.documents:
                if str(document.id) not in document_ids:
                    continue
                if document.status == "failed":
                    raise RuntimeError(f"document failed: reason {document.failure_reason}")
                if document.status == "read":
                    if document.read_engine != "rapidocr":
                        raise RuntimeError("a completed document did not use RapidOCR")
                    observed[str(document.id)] = document.read_engine
        if document_ids == observed.keys():
            return observed
        await asyncio.sleep(0.2)
    raise RuntimeError("not every uploaded document completed before the workload deadline")


async def register_staff(
    client: httpx.AsyncClient, base_url: str, prefix: str, password: str
) -> dict[str, str]:
    """Create a fresh synthetic account and return its CSRF request headers."""
    response = await client.post(
        "/api/auth/register",
        json={
            "username": prefix,
            "display_name": "Synthetic runtime staff",
            "password": password,
            "role": "staff",
        },
    )
    require_status(response, (200,))
    return {"Origin": base_url, "X-CSRF-Token": client.cookies["docket_csrf"]}


async def import_applications(
    client: httpx.AsyncClient, dataset: Dataset, prefix: str, headers: dict[str, str]
) -> dict[str, str]:
    """Import uniquely named copies and resolve their API identifiers."""
    renamed = dataclasses.replace(
        dataset,
        applications=tuple(
            dataclasses.replace(
                application, application_id=f"{prefix}-{application.application_id}"
            )
            for application in dataset.applications
        ),
    )
    response = await client.post(
        "/api/imports",
        files={"file": ("synthetic.csv", applications_csv(renamed).encode(), "text/csv")},
        headers=headers,
    )
    require_status(response, (201,))
    imported = ImportResultOut.model_validate_json(response.content)
    if imported.rows_created != 20 or imported.rows_rejected:
        raise RuntimeError("the synthetic import did not create every application")
    response = await client.get("/api/applications", params={"limit": 100})
    require_status(response, (200,))
    applications = ApplicationListOut.model_validate_json(response.content)
    identifiers = {
        application.application_ref.removeprefix(prefix + "-"): str(application.id)
        for application in applications.data
        if application.application_ref.startswith(prefix + "-")
    }
    if len(identifiers) != 20:
        raise RuntimeError("the benchmark's applications were not all visible on the first page")
    return identifiers


async def upload_seed(
    client: httpx.AsyncClient,
    dataset: Dataset,
    identifiers: dict[str, str],
    png_dir: Path,
    headers: dict[str, str],
) -> set[str]:
    """Queue all thirty labelled pages concurrently."""
    return set(
        await asyncio.gather(
            *(
                upload(
                    client,
                    identifiers[document.application_id],
                    document.file_name,
                    (png_dir / document.file_name).read_bytes(),
                    headers,
                )
                for document in dataset.documents
            )
        )
    )


async def mixed_requests(
    client: httpx.AsyncClient,
    application_id: str,
    base_url: str,
    prefix: str,
    password: str,
    headers: dict[str, str],
) -> tuple[list[str], list[int]]:
    """Submit maximum size uploads and password verification together."""
    maximum_pages = [maximum_png(index) for index in range(4)]
    large = asyncio.gather(
        *(
            upload(
                client,
                application_id,
                f"maximum-{index}.png",
                content,
                headers,
            )
            for index, content in enumerate(maximum_pages)
        )
    )
    logins = asyncio.gather(*(sign_in(base_url, prefix, password) for _ in range(4)))
    return await large, await logins


async def run(base_url: str, png_dir: Path, out: Path) -> int:
    """Create a synthetic staff account, import applications, then run mixed HTTP work."""
    if urlparse(base_url).hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("the benchmark only accepts an isolated local API")
    prefix = f"runtime-notask17-{secrets.token_hex(4)}"
    password = secrets.token_urlsafe(24)
    dataset = build_dataset()
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=base_url, timeout=180) as client:
        headers = await register_staff(client, base_url, prefix, password)
        identifiers = await import_applications(client, dataset, prefix, headers)
        documents = await upload_seed(client, dataset, identifiers, png_dir, headers)
        large, login_statuses = await mixed_requests(
            client,
            identifiers[dataset.applications[0].application_id],
            base_url,
            prefix,
            password,
            headers,
        )
        documents.update(large)
        completed = await await_read(
            client, set(identifiers.values()), documents, deadline_seconds=300
        )
        response = await client.get("/healthz")
        require_status(response, (200,))
    result = {
        "synthetic_applications": 20,
        "seed_documents": 30,
        "maximum_uploads": 4,
        "maximum_pixels": 25_000_000,
        "concurrent_logins": len(login_statuses),
        "completed_rapidocr_documents": len(completed),
        "unexpected_http_errors": 0,
        "elapsed_seconds": time.monotonic() - started,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(out.write_text, json.dumps(result, indent=2) + "\n")
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Drive an already running isolated container; container management belongs to the caller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8187")
    parser.add_argument("--png-dir", type=Path, default=Path("data/seed/png"))
    parser.add_argument("--out", type=Path, default=Path(".scratch/NOTASK-17/memory-runtime.json"))
    args = parser.parse_args(argv)
    return asyncio.run(run(args.base_url.rstrip("/"), args.png_dir, args.out))


if __name__ == "__main__":
    raise SystemExit(main())
