"""RapidOCR behind the gateway's `Engine` interface (ADR-0001). The only module that imports it.

The page is brought down to 640 px on its long side and flattened and straightened first, which is
what the measurement behind ADR-0001 used. Boxes are given back in pixels of the image that was
passed in, not of the smaller copy the engine saw, so a reader can draw them on the stored page.
The models ship inside the wheel: nothing is downloaded when a document is read.
"""

import logging
from importlib.metadata import version

import cv2
import numpy as np

from app.gateway.preprocess import preprocess
from app.gateway.types import OcrResult, OcrWord

MAX_SIDE = 640
ENGINE_NAME = "rapidocr"


def release() -> str:
    """The installed release, recorded with every call so a result can be traced to it."""
    return f"{ENGINE_NAME}-{version('rapidocr')}"


class RapidOcrEngine:
    """Loads the models once, then reads one image at a time."""

    name = ENGINE_NAME

    def __init__(self) -> None:
        from rapidocr import RapidOCR
        from rapidocr.utils.output import RapidOCROutput

        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
        self._ocr = RapidOCR()
        self._output_type = RapidOCROutput

    def read(self, image: bytes) -> OcrResult:
        pixels = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if pixels is None:
            msg = "the bytes are not an image"
            raise ValueError(msg)
        longest = max(pixels.shape[:2])
        scale = min(1.0, MAX_SIDE / longest)
        if scale < 1.0:
            pixels = cv2.resize(pixels, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        result = self._ocr(preprocess(np.asarray(pixels, dtype=np.uint8)))
        if not isinstance(result, self._output_type):
            msg = "the engine returned a partial result"
            raise TypeError(msg)
        texts = result.txts or ()
        scores = result.scores or ()
        boxes = result.boxes if result.boxes is not None else ()
        words = []
        for text, score, quad in zip(texts, scores, boxes, strict=False):
            xs, ys = quad[:, 0] / scale, quad[:, 1] / scale
            left, top = float(xs.min()), float(ys.min())
            words.append(
                OcrWord(
                    text=text,
                    confidence=float(score),
                    box=(left, top, float(xs.max()) - left, float(ys.max()) - top),
                )
            )
        return OcrResult(words=tuple(words))


def make_engine() -> RapidOcrEngine:
    """The factory the child process calls, so the models load there and not in the API."""
    return RapidOcrEngine()
