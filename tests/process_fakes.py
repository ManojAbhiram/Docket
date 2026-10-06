"""Engines the child-process tests run on the other side of the pipe.

They live in a module of their own because the child is started with `spawn`, which imports the
factory by name instead of copying it. An engine here does what the image bytes ask for.
"""

import os
import time

from app.gateway import OcrResult, OcrWord


class PidEngine:
    """Answers with the id of the process it runs in, so a test can tell children apart."""

    name = "fake"

    def read(self, image: bytes) -> OcrResult:
        if image == b"hang":
            time.sleep(60)
        if image == b"crash":
            os._exit(3)
        if image == b"boom":
            msg = "a message that carries SYN0945957"
            raise RuntimeError(msg)
        return OcrResult(
            words=(OcrWord(text=str(os.getpid()), confidence=0.9, box=(1.0, 2.0, 3.0, 4.0)),)
        )


def make_engine() -> PidEngine:
    return PidEngine()
