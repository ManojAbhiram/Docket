"""The opt-in OpenRouter Vision reader (ADR-0015, ADR-0014, REQ-030, REQ-031).

The model is a free one, so cost stays zero and the call count is the cap. Every test uses a mock
transport: no test reaches the network. The model's own words never leave the reader.
"""

import base64
import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from app.gateway import CallCapReachedError, CallRecord, EngineError
from app.gateway.vision import ENGINE_NAME, VisionReader

IMAGE = b"\x89PNG synthetic page"
MODEL = "google/gemma-4-31b-it:free"
KEY = "sk-or-v1-test-key-not-real"

MARKSHEET = {
    "document_type": "10th_marksheet",
    "fields": {
        "name": "Latha Sharma",
        "father_name": "Salim Sharma",
        "dob": "10/12/2006",
        "board": "Karnataka State Board",
        "roll_number": "SYN0945957",
        "marks": {"English": "59", "Hindi": "77"},
    },
}


class MemoryLedger:
    def __init__(self, made: int = 0) -> None:
        self.made = made
        self.records: list[CallRecord] = []

    def calls_made(self) -> int:
        return self.made + sum(1 for r in self.records if r.outcome != "refused")

    def record(self, record: CallRecord) -> None:
        self.records.append(record)


def reply(content: object, status: int = 200) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(status, json={"choices": [{"message": {"content": text}}]})


def reader_with(
    handler: Callable[[httpx.Request], httpx.Response],
    ledger: MemoryLedger | None = None,
    cap: int = 5,
) -> tuple[VisionReader, MemoryLedger]:
    ledger = ledger or MemoryLedger()
    reader = VisionReader(
        api_key=KEY,
        model=MODEL,
        ledger=ledger,
        cap=cap,
        timeout_seconds=5.0,
        transport=httpx.MockTransport(handler),
    )
    return reader, ledger


def test_a_marksheet_answer_becomes_fields_that_always_go_to_review() -> None:
    reader, ledger = reader_with(lambda _request: reply(MARKSHEET))

    result = reader.read(IMAGE, confidence_cutoff=0.98)

    assert result.doc_type == "10th_marksheet"
    assert result.engine == ENGINE_NAME
    by_name = {(f.field_name, f.subject): f for f in result.fields}
    assert by_name[("name", None)].value == "Latha Sharma"
    assert by_name[("marks", "English")].value == "59"
    # A model gives no score and no box, so none is invented; a person decides every field.
    assert all(f.confidence is None and f.box is None for f in result.fields)
    assert all(f.needs_review and f.review_reason == "low_confidence" for f in result.fields)
    assert [(r.engine, r.outcome, r.units, r.cost) for r in ledger.records] == [
        (ENGINE_NAME, "ok", len(result.fields), Decimal(0))
    ]


def test_a_field_the_model_left_out_is_kept_as_not_extracted() -> None:
    answer = {"document_type": "id_proof", "fields": {"name": "Latha Sharma"}}
    reader, _ = reader_with(lambda _request: reply(answer))

    fields = {f.field_name: f for f in reader.read(IMAGE, confidence_cutoff=0.9).fields}

    assert fields["dob"].review_reason == "not_extracted"
    assert fields["dob"].value == ""
    assert fields["document_number"].review_reason == "not_extracted"


def test_a_value_in_the_wrong_format_is_marked_format_invalid() -> None:
    answer = {
        "document_type": "id_proof",
        "fields": {"name": "Latha Sharma", "dob": "last spring", "document_number": "A"},
    }
    reader, _ = reader_with(lambda _request: reply(answer))

    fields = {f.field_name: f for f in reader.read(IMAGE, confidence_cutoff=0.9).fields}

    assert fields["dob"].review_reason == "format_invalid"
    assert fields["document_number"].review_reason == "format_invalid"


def test_an_unknown_document_type_has_no_fields() -> None:
    reader, _ = reader_with(lambda _request: reply({"document_type": "unknown", "fields": {}}))

    result = reader.read(IMAGE, confidence_cutoff=0.9)

    assert (result.doc_type, result.fields) == ("unknown", ())


def test_an_answer_wrapped_in_a_code_fence_is_still_read() -> None:
    fenced = "```json\n" + json.dumps(MARKSHEET) + "\n```"
    reader, _ = reader_with(lambda _request: reply(fenced))

    assert reader.read(IMAGE, confidence_cutoff=0.9).doc_type == "10th_marksheet"


def test_the_request_names_the_model_caps_the_tokens_and_sends_the_page_as_a_data_url() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return reply(MARKSHEET)

    reader, _ = reader_with(handler)
    reader.read(IMAGE, confidence_cutoff=0.9)

    (request,) = seen
    body = json.loads(request.content)
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert body["model"] == MODEL
    assert body["max_tokens"] == 600
    parts = body["messages"][0]["content"]
    url = next(p["image_url"]["url"] for p in parts if p["type"] == "image_url")
    assert url.startswith("data:image/")
    assert base64.b64decode(url.split(",", 1)[1]) == IMAGE
    assert KEY not in request.content.decode()


@pytest.mark.parametrize(
    ("handler", "label"),
    [
        (lambda _r: httpx.Response(429, json={"error": {"message": "secret detail"}}), "rate"),
        (lambda _r: httpx.Response(500, text="boom"), "server"),
        (lambda _r: reply("not json at all"), "not-json"),
        (lambda _r: reply({"document_type": "passport", "fields": {}}), "bad-type"),
        (lambda _r: reply({"fields": {}}), "no-type"),
        (lambda _r: httpx.Response(200, json={"choices": []}), "no-choice"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_a_bad_answer_is_an_engine_error_that_hides_the_provider_message(
    handler: Callable[[httpx.Request], httpx.Response], label: str
) -> None:
    reader, ledger = reader_with(handler)

    with pytest.raises(EngineError) as raised:
        reader.read(IMAGE, confidence_cutoff=0.9)

    assert "secret detail" not in str(raised.value)
    assert [(r.outcome, r.units) for r in ledger.records] == [("error", 0)]


def test_a_timeout_is_an_engine_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    reader, ledger = reader_with(handler)

    with pytest.raises(EngineError):
        reader.read(IMAGE, confidence_cutoff=0.9)
    assert ledger.records[0].outcome == "error"


def test_past_the_cap_no_request_is_made() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return reply(MARKSHEET)

    reader, ledger = reader_with(handler, MemoryLedger(made=2), cap=2)

    with pytest.raises(CallCapReachedError):
        reader.read(IMAGE, confidence_cutoff=0.9)

    assert calls == []
    assert [r.outcome for r in ledger.records] == ["refused"]
