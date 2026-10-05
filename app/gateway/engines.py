"""Engines behind the gateway. Only the recorded engine exists so far: CI makes no live calls."""

import hashlib
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.gateway.types import Engine, OcrResult, OcrWord, RecordingMissingError


class _RecordedWord(BaseModel):
    text: str
    confidence: float
    box: tuple[float, float, float, float]


class _Recording(BaseModel):
    words: list[_RecordedWord]


class RecordedEngine:
    """Replays answers saved earlier, keyed by the SHA-256 of the image. No network, no model."""

    name = "recorded"

    def __init__(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        self._recordings = TypeAdapter(dict[str, _Recording]).validate_json(text)

    def read(self, image: bytes) -> OcrResult:
        recording = self._recordings.get(hashlib.sha256(image).hexdigest())
        if recording is None:
            msg = "no recording for this image"
            raise RecordingMissingError(msg)
        return OcrResult(
            words=tuple(
                OcrWord(text=word.text, confidence=word.confidence, box=word.box)
                for word in recording.words
            )
        )


def build_engine(name: str, *, recording: Path) -> Engine:
    """Choose the engine by configured name, so callers never change when the engine does."""
    if name == "recorded":
        return RecordedEngine(recording)
    msg = f"unknown engine {name}"
    raise ValueError(msg)
