"""The opt-in OpenRouter Vision reader (ADR-0015, ADR-0014, REQ-030, REQ-031).

The model is a free one, so cost stays zero and the call count is the cap. Every test uses a mock
transport: no test reaches the network. The model's own words never leave the reader.
"""

import base64
import json
from collections.abc import Callable, Iterator
from decimal import Decimal

import httpx
import pytest

from app.gateway import CallCapReachedError, CallRecord, EngineError
from app.gateway.vision import (
    ENGINE_NAME,
    VisionBadAnswerError,
    VisionRateLimitedError,
    VisionReader,
    VisionTimeoutError,
    VisionUpstreamError,
)

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
    clock: Callable[[], float] | None = None,
) -> tuple[VisionReader, MemoryLedger]:
    ledger = ledger or MemoryLedger()
    reader = VisionReader(
        api_key=KEY,
        model=MODEL,
        ledger=ledger,
        cap=cap,
        timeout_seconds=5.0,
        transport=httpx.MockTransport(handler),
        **({} if clock is None else {"clock": clock}),
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


# Regression: ISSUE-001 [NOTASK-16], found by /qa on 2026-10-11. Seven of nine live free-model
# calls failed and every one was reported as a generic vision_error, so a rate limit, a provider
# fault and an unusable answer could not be told apart by a user, a log or the call ledger.
# Report: .gstack/qa-reports/run-20261011T100920Z/
def http_status(status: int) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(status, json={"error": {"message": "x"}})


def error_body(code: int) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _request: httpx.Response(200, json={"error": {"code": code, "message": "x"}})


@pytest.mark.parametrize(
    ("handler", "cause"),
    [
        (http_status(429), VisionRateLimitedError),
        (http_status(500), VisionUpstreamError),
        (error_body(429), VisionRateLimitedError),
        (error_body(502), VisionUpstreamError),
        (lambda _r: httpx.Response(200, json={"id": "gen-1"}), VisionBadAnswerError),
        (lambda _r: httpx.Response(200, json={"choices": []}), VisionBadAnswerError),
        (lambda _r: reply("not json at all"), VisionBadAnswerError),
        (lambda _r: reply({"document_type": "passport", "fields": {}}), VisionBadAnswerError),
    ],
    ids=["http-429", "http-500", "body-429", "body-502", "no-choices", "empty", "not-json", "type"],
)
def test_each_failure_names_its_cause_in_the_call_log(
    handler: Callable[[httpx.Request], httpx.Response], cause: type[Exception]
) -> None:
    reader, ledger = reader_with(handler)

    with pytest.raises(EngineError) as raised:
        reader.read(IMAGE, confidence_cutoff=0.9)

    assert isinstance(raised.value.__cause__, cause)
    assert ledger.records[0].error_class == cause.__name__


def test_a_connection_failure_is_an_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    reader, ledger = reader_with(handler)

    with pytest.raises(EngineError) as raised:
        reader.read(IMAGE, confidence_cutoff=0.9)

    assert isinstance(raised.value.__cause__, VisionUpstreamError)
    assert ledger.records[0].error_class == "VisionUpstreamError"


class Trickle(httpx.SyncByteStream):
    """A body that arrives in pieces, as a provider's keep-alive bytes do before the answer."""

    def __init__(self, answer: object) -> None:
        self._pieces = [b" ", b" ", json.dumps(answer).encode()]

    def __iter__(self) -> Iterator[bytes]:
        yield from self._pieces


def trickling(answer: object) -> Callable[[httpx.Request], httpx.Response]:
    body = {"choices": [{"message": {"content": json.dumps(answer)}}]}
    return lambda _request: httpx.Response(200, stream=Trickle(body))


def ticking(*seconds: float) -> Callable[[], float]:
    values = iter(seconds)
    return lambda: next(values)


# Regression: ISSUE-002 [NOTASK-16], found by /qa on 2026-10-11. The timeout was httpx's per read,
# and a provider that trickles bytes resets it, so a call ran 161 s or more against a 90 s setting.
# The sweeper then failed the document as interrupted and the serial worker stalled the queue.
# Report: .gstack/qa-reports/run-20261011T100920Z/
def test_a_provider_that_trickles_bytes_past_the_deadline_is_a_timeout() -> None:
    reader, ledger = reader_with(trickling(MARKSHEET), clock=ticking(0, 40, 80, 120))

    with pytest.raises(EngineError) as raised:
        reader.read(IMAGE, confidence_cutoff=0.9)

    assert isinstance(raised.value.__cause__, VisionTimeoutError)
    assert [r.outcome for r in ledger.records] == ["error"]


def test_a_trickling_answer_that_finishes_inside_the_deadline_is_read() -> None:
    reader, _ = reader_with(trickling(MARKSHEET), clock=ticking(0, 1, 2, 3, 4))

    assert reader.read(IMAGE, confidence_cutoff=0.9).doc_type == "10th_marksheet"
