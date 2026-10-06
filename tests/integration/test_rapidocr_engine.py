"""The real engine on synthetic pages (US-00-003, ADR-0001, REQ-007, REQ-044).

Runs RapidOCR, so each test loads the models (a few seconds). Pages are drawn here, with made-up
values, then blurred, skewed and shadowed the way a phone photo is. Nothing here uses a real
student document.
"""

import socket

import cv2
import numpy as np
import pytest

from app.domain.classify import classify
from app.domain.extract import extract_fields
from app.domain.match import fields_for
from app.gateway.process import ProcessEngine
from app.gateway.rapidocr_engine import RapidOcrEngine, make_engine

pytestmark = pytest.mark.integration

WIDTH, HEIGHT = 1280, 720
CUTOFF = 0.9804


def id_card() -> np.ndarray:
    page = np.full((HEIGHT, WIDTH, 3), 255, dtype=np.uint8)
    rows = [
        (60, "Identity Card", None),
        (220, "Name", "Latha Sharma"),
        (340, "Date of birth", "10/12/2006"),
        (460, "ID number", "SYNID12345678"),
    ]
    for y, label, value in rows:
        cv2.putText(page, label, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 3)
        if value:
            cv2.putText(page, value, (640, y), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 3)
    return page


def phone_photo(page: np.ndarray) -> np.ndarray:
    """Blur, a small skew and a shadow across one side, like a hand-held photo."""
    blurred = cv2.GaussianBlur(page, (5, 5), 1.2)
    turn = cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), 2.5, 1.0)
    skewed = cv2.warpAffine(blurred, turn, (WIDTH, HEIGHT), borderValue=(255, 255, 255))
    shade = np.linspace(1.0, 0.65, WIDTH, dtype=np.float32)[None, :, None]
    return np.asarray(skewed * shade, dtype=np.uint8)


def png(page: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", page)
    assert ok
    return bytes(encoded.tobytes())


def test_a_clean_page_is_read_into_words_with_confidences() -> None:
    words = RapidOcrEngine().read(png(id_card())).words

    joined = " ".join(w.text for w in words)
    assert "Latha Sharma" in joined
    assert "SYNID12345678" in joined
    assert all(0.0 <= w.confidence <= 1.0 for w in words)


def test_boxes_are_in_pixels_of_the_image_that_was_sent_not_the_smaller_copy_the_engine_saw() -> (
    None
):
    words = RapidOcrEngine().read(png(id_card())).words

    value = next(w for w in words if "Latha" in w.text)
    x, y, width, height = value.box
    assert 600 < x < 700
    assert 150 < y < 260
    assert x + width <= WIDTH
    assert y + height <= HEIGHT


def test_reading_opens_no_network_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        pytest.fail("the engine opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)

    words = RapidOcrEngine().read(png(id_card())).words

    assert words


def test_a_blurred_skewed_shadowed_photo_is_classified_and_every_field_is_read_or_flagged() -> None:
    words = RapidOcrEngine().read(png(phone_photo(id_card()))).words

    document_type = classify(words)
    fields = extract_fields(words, document_type, confidence_cutoff=CUTOFF)

    assert document_type == "id_proof"
    assert {f.field_name for f in fields} == fields_for(document_type)
    for field in fields:
        assert field.value or field.needs_review


def test_the_child_process_engine_reads_a_page_and_the_models_load_there_not_here() -> None:
    engine = ProcessEngine(make_engine, name="rapidocr", read_timeout=60.0, recycle_after=10)
    try:
        words = engine.read(png(id_card())).words

        assert any("Latha" in w.text for w in words)
        assert engine.child_pid is not None
    finally:
        engine.close()
