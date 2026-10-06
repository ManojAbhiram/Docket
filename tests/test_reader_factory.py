"""Choosing the engine and building the reader the worker calls (US-00-003, US-02-001, ADR-0011).

The reader is the gateway with the engine, the ledger and the cap already chosen. Callers never
change when the engine does.
"""

import hashlib
import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.gateway import CallCapReachedError, CallRecord
from app.gateway.process import ProcessEngine
from app.gateway.reader import build_reader, engine_version

IMAGE = b"synthetic page bytes"


class MemoryLedger:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []

    def calls_made(self) -> int:
        return sum(1 for record in self.records if record.outcome != "refused")

    def record(self, record: CallRecord) -> None:
        self.records.append(record)


def settings_for(tmp_path: Path, **overrides: object) -> Settings:
    recording = tmp_path / "recording.json"
    key = hashlib.sha256(IMAGE).hexdigest()
    words = [{"text": "Latha Sharma", "confidence": 0.99, "box": [1.0, 2.0, 3.0, 4.0]}]
    recording.write_text(json.dumps({key: {"words": words}}), encoding="utf-8")
    base: dict[str, object] = {
        "_env_file": None,
        "env": "test",
        "database_url": "postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        "gateway_engine": "recorded",
        "gateway_recording": recording,
    }
    return Settings.model_validate(base | overrides)


def test_the_reader_reads_through_the_gateway_and_logs_one_call(tmp_path: Path) -> None:
    ledger = MemoryLedger()
    reader = build_reader(settings_for(tmp_path), ledger)

    result = reader.read(IMAGE)

    assert [word.text for word in result.words] == ["Latha Sharma"]
    assert [(r.engine, r.outcome) for r in ledger.records] == [("recorded", "ok")]


def test_the_reader_refuses_a_call_past_the_configured_cap(tmp_path: Path) -> None:
    ledger = MemoryLedger()
    reader = build_reader(settings_for(tmp_path, gateway_call_cap=1), ledger)
    reader.read(IMAGE)

    with pytest.raises(CallCapReachedError):
        reader.read(IMAGE)

    assert [r.outcome for r in ledger.records] == ["ok", "refused"]


def test_an_unknown_engine_name_is_refused_when_the_reader_is_built(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown engine"):
        build_reader(settings_for(tmp_path, gateway_engine="mystery"), MemoryLedger())


def test_the_recorded_engine_needs_a_recording_file(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, gateway_recording=None)

    with pytest.raises(ValueError, match="GATEWAY_RECORDING"):
        build_reader(settings, MemoryLedger())


def test_the_real_engine_runs_in_a_child_process_that_is_not_started_until_the_first_read(
    tmp_path: Path,
) -> None:
    reader = build_reader(settings_for(tmp_path, gateway_engine="rapidocr"), MemoryLedger())
    try:
        assert isinstance(reader.engine, ProcessEngine)
        assert reader.engine.child_pid is None
    finally:
        reader.close()


def test_the_version_recorded_with_each_call_names_the_engine_and_its_release(
    tmp_path: Path,
) -> None:
    assert engine_version(settings_for(tmp_path, gateway_engine="rapidocr")).startswith("rapidocr-")
    assert engine_version(settings_for(tmp_path)) == "recorded-1"
