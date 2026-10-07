"""Tesseract behind the Engine interface, so the runner-up is scored by the same code as the winner.

pytesseract is an eval-only dependency (evals/requirements-ocr.txt), so it is imported when the
engine is built and the app and its tests never need it. The image goes through the same
preprocessing the app applies before RapidOCR, so both engines read the same pixels.
"""

import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from app.gateway.preprocess import preprocess
from app.gateway.types import OcrResult, OcrWord

_PERCENT = 100
_PHRASE_GAP = 0.8


@dataclass(frozen=True)
class _Token:
    text: str
    confidence: float
    left: float
    top: float
    width: float
    height: float
    line: tuple[int, int, int]


def words_from_data(data: Mapping[str, Sequence[object]]) -> tuple[OcrWord, ...]:
    """Phrases, not single tokens: neighbours on one line with a word-space gap are joined.

    RapidOCR returns one box per text segment ("Date of birth", "Latha Sharma"), and the
    extractor reads a label and a value as such segments. Tesseract returns one box per token,
    so tokens are merged here to give both engines the same granularity. A gap wider than
    `_PHRASE_GAP` line heights (a label and its value in a table) keeps them apart.
    """
    tokens: list[_Token] = []
    rows = zip(
        data["text"], data["conf"], data["left"], data["top"], data["width"], data["height"],
        data["block_num"], data["par_num"], data["line_num"],
        strict=True,
    )  # fmt: skip
    for text, conf, left, top, width, height, block, par, line in rows:
        if not str(text).strip():
            continue
        tokens.append(
            _Token(
                text=str(text).strip(),
                confidence=max(float(str(conf)), 0.0) / _PERCENT,
                left=float(str(left)),
                top=float(str(top)),
                width=float(str(width)),
                height=float(str(height)),
                line=(int(str(block)), int(str(par)), int(str(line))),
            )
        )
    phrases: list[list[_Token]] = []
    for token in tokens:
        if phrases and _joins(phrases[-1][-1], token):
            phrases[-1].append(token)
        else:
            phrases.append([token])
    return tuple(_phrase(parts) for parts in phrases)


def _joins(previous: _Token, token: _Token) -> bool:
    gap = token.left - (previous.left + previous.width)
    return token.line == previous.line and gap <= _PHRASE_GAP * max(previous.height, token.height)


def _phrase(parts: Sequence[_Token]) -> OcrWord:
    left = min(t.left for t in parts)
    top = min(t.top for t in parts)
    right = max(t.left + t.width for t in parts)
    bottom = max(t.top + t.height for t in parts)
    return OcrWord(
        text=" ".join(t.text for t in parts),
        confidence=sum(t.confidence for t in parts) / len(parts),
        box=(left, top, right - left, bottom - top),
    )


class TesseractEngine:
    name = "tesseract"

    def __init__(self, lang: str = "eng", psm: int = 11) -> None:
        self._pytesseract = importlib.import_module("pytesseract")
        self._lang = lang
        self._psm = psm

    def read(self, image: bytes) -> OcrResult:
        pixels = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if pixels is None:
            msg = "the bytes are not an image"
            raise ValueError(msg)
        rgb = cv2.cvtColor(preprocess(np.asarray(pixels, dtype=np.uint8)), cv2.COLOR_BGR2RGB)
        data = self._pytesseract.image_to_data(
            rgb,
            lang=self._lang,
            config=f"--psm {self._psm}",
            output_type=self._pytesseract.Output.DICT,
        )
        return OcrResult(words=words_from_data(data))
