"""The engine in one long-lived child process that can be killed (ADR-0011).

A read that hangs would hold the API with it, so the engine runs in a child. The parent sends an
image down a pipe and waits at most `read_timeout` seconds; past that the child is killed and the
next read starts a new one. The child is also replaced after `recycle_after` documents, so memory
growth in the engine stays bounded. Only an error's class name crosses the pipe, because the
engine's own message can carry a value read from a page.
"""

import multiprocessing
import threading
from collections.abc import Callable
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess

from app.gateway.types import Engine, EngineError, OcrResult, OcrWord

type _Box = tuple[float, float, float, float]
type _Wire = list[tuple[str, float, _Box]]
type EngineFactory = Callable[[], Engine]

_JOIN_SECONDS = 5.0


class EngineTimeoutError(EngineError):
    """A read ran past its limit and the child was killed."""

    status_code = 504
    code = "read_timeout"


def _serve(connection: Connection, factory: EngineFactory) -> None:
    """The child's loop: build the engine once, then read every image it is sent."""
    engine = factory()
    while True:
        try:
            image = connection.recv()
        except EOFError:
            return
        try:
            result = engine.read(image)
        except Exception as exc:
            connection.send(("error", type(exc).__name__))
            continue
        wire: _Wire = [(w.text, w.confidence, w.box) for w in result.words]
        connection.send(("ok", wire))


class ProcessEngine:
    """An `Engine` whose work happens in a child process. Reads are one at a time."""

    def __init__(
        self,
        factory: EngineFactory,
        *,
        name: str,
        read_timeout: float,
        recycle_after: int,
    ) -> None:
        self.name = name
        self._factory = factory
        self._read_timeout = read_timeout
        self._recycle_after = recycle_after
        self._lock = threading.Lock()
        self._process: BaseProcess | None = None
        self._connection: Connection | None = None
        self._served = 0

    @property
    def child_pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    def read(self, image: bytes) -> OcrResult:
        with self._lock:
            connection = self._ensure_child()
            try:
                connection.send(image)
                if not connection.poll(self._read_timeout):
                    self._stop_child()
                    msg = "the engine did not answer in time"
                    raise EngineTimeoutError(msg)
                kind, payload = connection.recv()
            except (EOFError, OSError) as exc:
                self._stop_child()
                msg = "the engine process stopped"
                raise EngineError(msg) from exc
            self._served += 1
            if kind == "error":
                msg = f"the engine failed with {payload}"
                raise EngineError(msg)
            if self._served >= self._recycle_after:
                self._stop_child()
            return OcrResult(
                words=tuple(OcrWord(text=t, confidence=c, box=b) for t, c, b in payload)
            )

    def close(self) -> None:
        with self._lock:
            self._stop_child()

    def _ensure_child(self) -> Connection:
        if self._process is not None and self._process.is_alive() and self._connection:
            return self._connection
        self._stop_child()
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_serve, args=(child, self._factory), daemon=True)
        process.start()
        child.close()
        self._process, self._connection, self._served = process, parent, 0
        return parent

    def _stop_child(self) -> None:
        process, connection = self._process, self._connection
        self._process, self._connection = None, None
        if connection is not None:
            connection.close()
        if process is not None:
            if process.is_alive():
                process.kill()
            process.join(_JOIN_SECONDS)
            process.close()
