"""Upload and list documents against a real Postgres (US-00-002).

Needs `make db`, `make migrate` and the `poppler-utils` package for the PDF case. Images are
synthetic and generated here. AC-4 (the newer document of a type becomes current, the older is
kept) is decided when a document is read, and is proved in `test_document_queue.py`; here the
upload keeps every file and never replaces one.
"""

import hashlib
from uuid import UUID

import cv2
import numpy as np
import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.integration.helpers import SAME_ORIGIN, csrf_header, seed_user, sign_in

pytestmark = pytest.mark.integration

TWO_PAGE_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] >> endobj
4 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] >> endobj
trailer << /Root 1 0 R /Size 5 >>
%%EOF
"""
ACCEPTED = "JPG, PNG or PDF"


def picture(kind: str, shade: int = 90, size: int = 64) -> bytes:
    pixels = np.full((size, size, 3), shade, dtype=np.uint8)
    ok, encoded = cv2.imencode(f".{kind}", pixels)
    assert ok
    return bytes(encoded.tobytes())


async def new_application(connection: AsyncConnection, ref: str = "SYN-APP-001") -> UUID:
    row = await connection.execute(
        text(
            "INSERT INTO applications (application_ref, full_name, father_name, date_of_birth, "
            "board, roll_number, marks, category) VALUES (:ref, 'A B', 'C D', '2006-01-01', "
            "'CBSE', :roll, '{}', 'General') RETURNING id"
        ),
        {"ref": ref, "roll": f"R-{ref}"},
    )
    application_id: UUID = row.scalar_one()
    return application_id


async def send(
    client: AsyncClient,
    application_id: UUID | str,
    data: bytes,
    *,
    content_type: str,
    headers: dict[str, str] | None = None,
) -> Response:
    return await client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": ("scan", data, content_type)},
        headers=headers if headers is not None else csrf_header(client),
    )


async def staff(client: AsyncClient, connection: AsyncConnection) -> UUID:
    user_id = await seed_user(connection, "staff.demo", "staff")
    await sign_in(client, "staff.demo")
    return user_id


async def stored_rows(connection: AsyncConnection) -> list[tuple[str, str, int, str]]:
    result = await connection.execute(
        text(
            "SELECT d.source_content_type, d.sha256, d.size_bytes, b.content_type "
            "FROM documents d JOIN document_blobs b ON b.document_id = d.id ORDER BY d.created_at"
        )
    )
    return [(r[0], r[1], r[2], r[3]) for r in result.all()]


async def test_a_png_is_stored_against_the_application_and_queued_for_reading(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    user_id = await staff(api, connection)
    application_id = await new_application(connection)
    png = picture("png")

    response = await send(api, application_id, png, content_type="image/png")

    assert response.status_code == 202
    body = response.json()
    assert body["application_id"] == str(application_id)
    assert (body["status"], body["is_current"], body["detected_type"]) == ("uploaded", True, None)
    assert "content" not in body
    assert await stored_rows(connection) == [
        ("image/png", hashlib.sha256(png).hexdigest(), len(png), "image/png")
    ]
    by = (await connection.execute(text("SELECT uploaded_by FROM documents"))).scalar_one()
    assert by == user_id


async def test_a_jpeg_is_accepted_and_stored_as_a_jpeg(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(api, application_id, picture("jpg"), content_type="image/jpeg")

    assert response.status_code == 202
    assert [row[3] for row in await stored_rows(connection)] == ["image/jpeg"]


async def test_only_the_first_page_of_a_pdf_is_kept_as_a_jpeg_and_the_pdf_itself_is_not(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(api, application_id, TWO_PAGE_PDF, content_type="application/pdf")

    assert response.status_code == 202
    rows = await stored_rows(connection)
    assert [(r[0], r[3]) for r in rows] == [("application/pdf", "image/jpeg")]
    blob = (await connection.execute(text("SELECT content FROM document_blobs"))).scalar_one()
    assert bytes(blob).startswith(b"\xff\xd8\xff")
    assert b"%PDF" not in bytes(blob)
    decoded = cv2.imdecode(np.frombuffer(bytes(blob), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    height, width = decoded.shape[:2]
    assert width > height


@pytest.mark.parametrize(
    ("data", "declared"),
    [
        (b"GIF89a....", "image/gif"),
        (b"plain text", "text/plain"),
        (picture("jpg"), "image/png"),
        (TWO_PAGE_PDF, "image/png"),
        (b"MZ\x90\x00 not an image", "image/jpeg"),
    ],
)
async def test_any_other_format_is_refused_naming_the_accepted_ones_and_nothing_is_stored(
    api: AsyncClient, connection: AsyncConnection, data: bytes, declared: str
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(api, application_id, data, content_type=declared)

    assert response.status_code == 415
    assert ACCEPTED in response.json()["error"]["message"]
    assert await stored_rows(connection) == []


async def test_a_file_over_the_size_cap_is_refused_with_413_and_nothing_is_stored(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(
        api, application_id, b"\x89PNG\r\n\x1a\n" + b"0" * 70_000, content_type="image/png"
    )

    assert response.status_code == 413
    assert await stored_rows(connection) == []


async def test_an_image_with_too_many_pixels_is_refused_before_it_is_decoded(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    huge = bytearray(picture("png"))
    huge[16:24] = (60_000).to_bytes(4, "big") + (60_000).to_bytes(4, "big")

    response = await send(api, application_id, bytes(huge), content_type="image/png")

    assert response.status_code == 422
    assert await stored_rows(connection) == []


async def test_a_pdf_that_cannot_be_read_is_refused_without_the_tool_message(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(api, application_id, b"%PDF-1.4 broken", content_type="application/pdf")

    assert response.status_code == 422
    assert "poppler" not in response.text.lower()
    assert await stored_rows(connection) == []


async def test_the_same_bytes_sent_again_return_the_existing_document_and_store_nothing_new(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    png = picture("png")
    first = await send(api, application_id, png, content_type="image/png")

    again = await send(api, application_id, png, content_type="image/png")

    assert (first.status_code, again.status_code) == (202, 200)
    assert again.json()["id"] == first.json()["id"]
    assert len(await stored_rows(connection)) == 1


async def test_a_different_file_for_the_same_application_is_stored_and_the_first_is_kept(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)
    first = await send(api, application_id, picture("png", 60), content_type="image/png")

    second = await send(api, application_id, picture("png", 200), content_type="image/png")

    assert second.status_code == 202
    assert second.json()["id"] != first.json()["id"]
    assert len(await stored_rows(connection)) == 2


async def test_the_same_bytes_for_another_application_are_a_new_document(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    one = await new_application(connection, "SYN-APP-001")
    two = await new_application(connection, "SYN-APP-002")
    png = picture("png")

    await send(api, one, png, content_type="image/png")
    second = await send(api, two, png, content_type="image/png")

    assert second.status_code == 202
    assert len(await stored_rows(connection)) == 2


async def test_a_verifier_may_not_upload_and_an_anonymous_caller_gets_401(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    application_id = await new_application(connection)
    png = picture("png")
    anonymous = await send(api, application_id, png, content_type="image/png", headers=SAME_ORIGIN)
    await seed_user(connection, "verifier.demo", "verifier")
    await sign_in(api, "verifier.demo")

    refused = await send(api, application_id, png, content_type="image/png")

    assert (anonymous.status_code, refused.status_code) == (401, 403)
    assert await stored_rows(connection) == []


async def test_an_upload_without_the_csrf_token_is_refused(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await send(
        api, application_id, picture("png"), content_type="image/png", headers=SAME_ORIGIN
    )

    assert response.status_code == 403
    assert await stored_rows(connection) == []


async def test_an_unknown_or_erased_application_is_404_and_a_bad_id_is_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    erased = await new_application(connection, "SYN-APP-009")
    await connection.execute(
        text("UPDATE applications SET erased_at = now() WHERE id = :id"), {"id": erased}
    )
    png = picture("png")

    unknown = await send(api, "0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b", png, content_type="image/png")
    gone = await send(api, erased, png, content_type="image/png")
    malformed = await send(api, "not-a-uuid", png, content_type="image/png")

    assert (unknown.status_code, gone.status_code, malformed.status_code) == (404, 404, 422)


async def test_a_request_with_no_file_is_refused_with_422(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)
    application_id = await new_application(connection)

    response = await api.post(
        f"/api/applications/{application_id}/documents", headers=csrf_header(api)
    )

    assert response.status_code == 422


async def test_the_document_list_is_newest_first_and_open_to_either_role(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await seed_user(connection, "verifier.demo", "verifier")
    application_id = await new_application(connection)
    for number in (1, 2, 3):
        await connection.execute(
            text(
                "INSERT INTO documents (application_id, uploaded_by, source_content_type, "
                "sha256, size_bytes, created_at) SELECT :app, id, 'image/png', :sha, 10, "
                "now() + make_interval(mins => :n) FROM users LIMIT 1"
            ),
            {"app": application_id, "sha": f"{number:064x}", "n": number},
        )
    assert (await api.get(f"/api/applications/{application_id}/documents")).status_code == 401
    await sign_in(api, "verifier.demo")

    first = (
        await api.get(f"/api/applications/{application_id}/documents", params={"limit": 2})
    ).json()
    second = (
        await api.get(
            f"/api/applications/{application_id}/documents",
            params={"limit": 2, "cursor": first["page"]["next_cursor"]},
        )
    ).json()

    assert [len(first["data"]), len(second["data"])] == [2, 1]
    assert first["page"]["has_more"] is True
    assert second["page"]["has_more"] is False
    ids = [d["id"] for d in first["data"] + second["data"]]
    assert len(set(ids)) == 3


async def test_listing_the_documents_of_an_unknown_application_is_404(
    api: AsyncClient, connection: AsyncConnection
) -> None:
    await staff(api, connection)

    response = await api.get("/api/applications/0192b1c2-7f3a-7c4e-9a1b-2c3d4e5f6a7b/documents")

    assert response.status_code == 404
