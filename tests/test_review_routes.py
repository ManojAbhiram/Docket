"""The review routes with the store faked, so they run without a database (US-00-006).

The integration tests prove the SQL; these prove what the routes do with what the store returns:
the ETag, the 404s and the fixed headers on the image.
"""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.applications.deps import get_review_store
from app.api.auth.deps import current_user
from app.db.repositories.application_detail import (
    ApplicationDetail,
    DocumentDetail,
    FieldRecord,
    StoredPage,
)
from app.domain.auth import SessionUser

APPLICATION_ID = UUID("0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b")
DOCUMENT_ID = UUID("0192b1c3-1a2b-7c4e-9a1b-2c3d4e5f6a7c")
STAMP = datetime(2026, 10, 5, 9, 12, 41, tzinfo=UTC)


class FakeStore:
    def __init__(self, *, found: bool = True, page: StoredPage | None = None) -> None:
        self.found = found
        self.page = page

    async def get_detail(self, application_id: UUID) -> ApplicationDetail | None:
        if not self.found:
            return None
        field = FieldRecord(
            id=1,
            field_name="name",
            subject=None,
            value="Meera Nair",
            application_value="Latha Sharma",
            confidence=0.99,
            box=[1.0, 2.0, 3.0, 4.0],
            match_result="mismatch",
            needs_review=True,
            review_reason="mismatch",
        )
        document = DocumentDetail(
            id=DOCUMENT_ID,
            application_id=application_id,
            detected_type="10th_marksheet",
            status="read",
            failure_reason=None,
            is_current=True,
            created_at=STAMP,
            fields=(field,),
        )
        return ApplicationDetail(
            id=application_id,
            application_ref="SYN-APP-001",
            full_name="Latha Sharma",
            father_name="Salim Sharma",
            date_of_birth=date(2006, 12, 10),
            board="CBSE",
            roll_number="SYN0945957",
            marks={"English": 59},
            category="General",
            status="needs_review",
            rejected=False,
            created_at=STAMP,
            updated_at=STAMP,
            documents=(document,),
        )

    async def get_image(self, document_id: UUID) -> StoredPage | None:
        return self.page


@pytest.fixture
def signed_in(app: FastAPI) -> FastAPI:
    async def verifier() -> SessionUser:
        return SessionUser(id=UUID(int=1), display_name="Demo Verifier", role="verifier")

    app.dependency_overrides[current_user] = verifier
    return app


def serve(app: FastAPI, store: FakeStore) -> None:
    app.dependency_overrides[get_review_store] = lambda: store


async def test_the_detail_carries_the_etag_and_the_value_beside_the_value(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    serve(signed_in, FakeStore())

    response = await client.get(f"/api/applications/{APPLICATION_ID}")

    assert response.status_code == 200
    assert response.headers["etag"] == '"2026-10-05T09:12:41+00:00"'
    field = response.json()["documents"][0]["fields"][0]
    assert (field["value"], field["application_value"], field["review_reason"]) == (
        "Meera Nair",
        "Latha Sharma",
        "mismatch",
    )


async def test_an_application_the_store_does_not_have_is_404(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    serve(signed_in, FakeStore(found=False))

    response = await client.get(f"/api/applications/{APPLICATION_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_the_image_is_served_with_fixed_headers_and_a_name_made_from_the_id(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    serve(signed_in, FakeStore(page=StoredPage(content_type="image/jpeg", content=b"\xff\xd8\xff")))

    response = await client.get(f"/api/documents/{DOCUMENT_ID}/image")

    assert response.content == b"\xff\xd8\xff"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert (
        response.headers["content-disposition"] == f'inline; filename="document-{DOCUMENT_ID}.jpg"'
    )


async def test_a_document_the_store_does_not_have_is_404(
    signed_in: FastAPI, client: AsyncClient
) -> None:
    serve(signed_in, FakeStore(page=None))

    assert (await client.get(f"/api/documents/{DOCUMENT_ID}/image")).status_code == 404
