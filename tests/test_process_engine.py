"""The engine in a child process that can be killed (US-00-003, ADR-0011).

A read that hangs must not hold the API: the child is killed at the timeout and the next read starts
a new one. The engine's own messages never cross the pipe, because they can carry a value.
"""

import os
import time
from collections.abc import Iterator

import pytest

from app.gateway import EngineError
from app.gateway.process import EngineTimeoutError, ProcessEngine
from tests.process_fakes import make_engine


@pytest.fixture
def engine() -> Iterator[ProcessEngine]:
    child = ProcessEngine(make_engine, name="fake", read_timeout=3.0, recycle_after=3)
    yield child
    child.close()


def pid_of(result_text: str) -> int:
    return int(result_text)


def test_a_read_runs_in_another_process_and_returns_the_words(engine: ProcessEngine) -> None:
    result = engine.read(b"page")

    assert pid_of(result.words[0].text) != os.getpid()
    assert result.words[0].box == (1.0, 2.0, 3.0, 4.0)
    assert result.words[0].confidence == 0.9


def test_consecutive_reads_use_the_same_child(engine: ProcessEngine) -> None:
    first = pid_of(engine.read(b"page").words[0].text)
    second = pid_of(engine.read(b"page").words[0].text)

    assert first == second


def test_a_read_that_runs_past_the_timeout_kills_the_child_and_says_so() -> None:
    engine = ProcessEngine(make_engine, name="fake", read_timeout=1.0, recycle_after=100)
    try:
        engine.read(b"page")
        child = engine.child_pid
        started = time.monotonic()

        with pytest.raises(EngineTimeoutError):
            engine.read(b"hang")

        assert time.monotonic() - started < 6
        assert child is not None
        with pytest.raises(ProcessLookupError):
            os.kill(child, 0)
    finally:
        engine.close()


def test_the_read_after_a_timeout_starts_a_fresh_child() -> None:
    engine = ProcessEngine(make_engine, name="fake", read_timeout=1.0, recycle_after=100)
    try:
        before = pid_of(engine.read(b"page").words[0].text)
        with pytest.raises(EngineTimeoutError):
            engine.read(b"hang")

        after = pid_of(engine.read(b"page").words[0].text)

        assert after != before
    finally:
        engine.close()


def test_a_child_that_dies_is_an_engine_error_not_a_timeout_and_the_next_read_works(
    engine: ProcessEngine,
) -> None:
    with pytest.raises(EngineError) as raised:
        engine.read(b"crash")

    assert not isinstance(raised.value, EngineTimeoutError)
    assert pid_of(engine.read(b"page").words[0].text) != os.getpid()


def test_an_error_inside_the_engine_crosses_as_a_class_name_never_the_message(
    engine: ProcessEngine,
) -> None:
    with pytest.raises(EngineError) as raised:
        engine.read(b"boom")

    assert "SYN0945957" not in str(raised.value)
    assert "SYN0945957" not in repr(raised.value.__cause__)


def test_the_child_is_replaced_after_the_configured_number_of_documents(
    engine: ProcessEngine,
) -> None:
    pids = [pid_of(engine.read(b"page").words[0].text) for _ in range(4)]

    assert pids[0] == pids[1] == pids[2]
    assert pids[3] != pids[0]


def test_closing_ends_the_child() -> None:
    engine = ProcessEngine(make_engine, name="fake", read_timeout=3.0, recycle_after=10)
    engine.read(b"page")
    child = engine.child_pid
    assert child is not None

    engine.close()

    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
    assert engine.child_pid is None
