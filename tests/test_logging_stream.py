"""Log lines follow stdout when it is swapped, so a test runner cannot leave a closed stream."""

import io
import sys

import pytest
import structlog

from app.core.logging import configure_logging


def test_log_lines_go_to_the_current_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_logging("info", "json")
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)

    structlog.get_logger("stream-test").info("after the swap")

    assert "after the swap" in buffer.getvalue()
