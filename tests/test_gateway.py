"""The OCR gateway: one function in front of every engine (US-02-001, REQ-030 to REQ-034, REQ-044).

Every test here fails until `app/gateway/` exists. The ledger and engines are small fakes of the two
interfaces the gateway owns, so no database, engine or network is needed.
"""

import ast
import hashlib
import json
import socket
from decimal import Decimal
from pathlib import Path

import pytest

from app.gateway import (
    CallCapReachedError,
    CallRecord,
    EngineError,
    OcrResult,
    OcrWord,
    RecordingMissingError,
    read_document,
)
from app.gateway.engines import RecordedEngine, build_engine

IMAGE = b"synthetic page bytes"
WORDS = (
    OcrWord(text="Latha Sharma", confidence=0.99, box=(10.0, 20.0, 100.0, 22.0)),
    OcrWord(text="SYN0945957", confidence=0.97, box=(10.0, 60.0, 90.0, 22.0)),
)


class MemoryLedger:
    """The call log, kept in a list. The real one writes the `gateway_calls` table."""

    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def calls_made(self) -> int:
        return sum(1 for record in self.records if record.outcome != "refused")

    def record(self, record: CallRecord) -> None:
        self.records.append(record)


class FakeEngine:
    """An engine that returns what it was given, or raises, and counts its calls."""

    def __init__(self, name: str, words: tuple[OcrWord, ...] = WORDS, fail: bool = False) -> None:
        self.name = name
        self.words = words
        self.fail = fail
        self.calls = 0

    def read(self, image: bytes) -> OcrResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("decoder crashed")
        return OcrResult(words=self.words)


def test_a_call_returns_the_engine_result_and_logs_one_ok_row() -> None:
    ledger = MemoryLedger()
    engine = FakeEngine("fake-a")

    result = read_document(IMAGE, engine=engine, ledger=ledger, cap=10)

    assert result.words == WORDS
    assert [(r.engine, r.outcome, r.units) for r in ledger.records] == [("fake-a", "ok", 2)]


def test_every_call_records_zero_cost_and_a_non_negative_latency() -> None:
    ledger = MemoryLedger()

    read_document(IMAGE, engine=FakeEngine("fake-a"), ledger=ledger, cap=10)

    record = ledger.records[0]
    assert record.cost == Decimal(0)
    assert isinstance(record.duration_ms, int)
    assert record.duration_ms >= 0


def test_an_engine_failure_is_logged_as_error_and_raised_without_the_message() -> None:
    ledger = MemoryLedger()

    with pytest.raises(EngineError) as raised:
        read_document(IMAGE, engine=FakeEngine("fake-a", fail=True), ledger=ledger, cap=10)

    assert [r.outcome for r in ledger.records] == ["error"]
    assert "decoder crashed" not in str(raised.value)


def test_a_call_past_the_cap_is_refused_logged_and_never_reaches_the_engine() -> None:
    ledger = MemoryLedger()
    engine = FakeEngine("fake-a")
    read_document(IMAGE, engine=engine, ledger=ledger, cap=1)

    with pytest.raises(CallCapReachedError):
        read_document(IMAGE, engine=engine, ledger=ledger, cap=1)

    assert engine.calls == 1
    assert [r.outcome for r in ledger.records] == ["ok", "refused"]


def test_a_refused_call_does_not_use_up_the_cap() -> None:
    ledger = MemoryLedger()
    engine = FakeEngine("fake-a")
    read_document(IMAGE, engine=engine, ledger=ledger, cap=1)
    for _ in range(3):
        with pytest.raises(CallCapReachedError):
            read_document(IMAGE, engine=engine, ledger=ledger, cap=1)

    assert ledger.calls_made() == 1


def test_two_engines_give_the_same_result_shape_to_the_same_caller() -> None:
    first = read_document(IMAGE, engine=FakeEngine("fake-a"), ledger=MemoryLedger(), cap=10)
    second = read_document(IMAGE, engine=FakeEngine("fake-b"), ledger=MemoryLedger(), cap=10)

    assert type(first) is type(second)
    assert first.words == second.words


def test_a_recorded_engine_replays_the_answer_for_the_same_image(tmp_path: Path) -> None:
    recording = tmp_path / "recording.json"
    key = hashlib.sha256(IMAGE).hexdigest()
    recording.write_text(
        json.dumps(
            {
                key: {
                    "words": [
                        {"text": "Latha Sharma", "confidence": 0.99, "box": [10, 20, 100, 22]},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = RecordedEngine(recording).read(IMAGE)

    assert result.words == (
        OcrWord(text="Latha Sharma", confidence=0.99, box=(10.0, 20.0, 100.0, 22.0)),
    )


def test_a_recorded_engine_makes_no_network_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recording = tmp_path / "recording.json"
    key = hashlib.sha256(IMAGE).hexdigest()
    recording.write_text(json.dumps({key: {"words": []}}), encoding="utf-8")

    def refuse(*_args: object, **_kwargs: object) -> None:
        pytest.fail("the recorded engine opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)

    RecordedEngine(recording).read(IMAGE)


def test_a_recorded_engine_refuses_an_image_it_has_no_recording_for(tmp_path: Path) -> None:
    recording = tmp_path / "recording.json"
    recording.write_text("{}", encoding="utf-8")

    with pytest.raises(RecordingMissingError):
        RecordedEngine(recording).read(b"an image nobody recorded")


def test_the_engine_is_chosen_by_name_and_an_unknown_name_is_refused(tmp_path: Path) -> None:
    recording = tmp_path / "recording.json"
    recording.write_text("{}", encoding="utf-8")

    assert isinstance(build_engine("recorded", recording=recording), RecordedEngine)
    with pytest.raises(ValueError, match="unknown engine"):
        build_engine("no-such-engine", recording=recording)


def test_no_module_outside_the_gateway_imports_an_engine_client() -> None:
    """AC-US-02-001-1: an engine import anywhere else would escape the cap and the log."""
    forbidden = {"rapidocr", "onnxruntime"}
    gateway = Path("app/gateway")
    offenders: list[str] = []
    for path in sorted(Path("app").rglob("*.py")):
        if gateway in path.parents:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            if names & forbidden:
                offenders.append(str(path))

    assert offenders == []
