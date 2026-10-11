"""The opt-in OpenRouter Vision reader (ADR-0015).

One request per page to a free vision model. Nothing here is trusted: the answer is parsed, its
shape checked, and every field is marked for review because a model gives no confidence and no box.
The provider's own message is never kept, because it can echo a value from the page (REQ-044).
"""

import base64
import json
import re
from typing import Literal, cast

import httpx
from pydantic import BaseModel, ValidationError

from app.domain.extract import FIELD_ORDER, ExtractedField, ReviewReason, is_valid_value
from app.domain.match import fields_for
from app.domain.processing import ProcessedDocument
from app.gateway.core import run_call
from app.gateway.types import CallLedger

ENGINE_NAME = "openrouter"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOKENS = 600

_PROMPT = (
    "You read one scanned admissions document. Reply with JSON only, no prose, in this shape: "
    '{"document_type": "10th_marksheet" | "12th_marksheet" | "id_proof" | '
    '"transfer_certificate" | "unknown", "fields": {"name": "", "father_name": "", "dob": "", '
    '"board": "", "roll_number": "", "document_number": "", "marks": {"<subject>": "<mark>"}}}. '
    "Copy values exactly as printed. Leave out a field the document does not show."
)
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_JPEG = b"\xff\xd8"

DocumentType = Literal[
    "10th_marksheet", "12th_marksheet", "id_proof", "transfer_certificate", "unknown"
]
Scalar = str | int | float


class VisionTimeoutError(Exception):
    """The provider did not answer in time. Only the class reaches the worker, never a message."""


class _Answer(BaseModel):
    document_type: DocumentType
    fields: dict[str, Scalar | dict[str, Scalar] | None] = {}


class VisionReader:
    """`read` for one image through OpenRouter, under the same cap and call log as OCR."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        ledger: CallLedger,
        cap: int,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._model = model
        self._ledger = ledger
        self._cap = cap
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport)

    def read(self, image: bytes, *, confidence_cutoff: float) -> ProcessedDocument:
        """Ask the model, then turn its answer into the shared result. Any failure is an error."""
        del confidence_cutoff  # the worker's reader interface passes it; a model gives no score
        return run_call(
            ENGINE_NAME,
            lambda: self._ask(image),
            ledger=self._ledger,
            cap=self._cap,
            units=lambda document: len(document.fields),
        )

    def close(self) -> None:
        self._client.close()

    def _ask(self, image: bytes) -> ProcessedDocument:
        try:
            response = self._post(image)
        except httpx.TimeoutException as exc:
            raise VisionTimeoutError from exc
        response.raise_for_status()
        answer = _parse(_content(response))
        return ProcessedDocument(
            doc_type=answer.document_type,
            fields=_fields(answer),
            engine=ENGINE_NAME,
        )

    def _post(self, image: bytes) -> httpx.Response:
        return self._client.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "max_tokens": MAX_TOKENS,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {"type": "image_url", "image_url": {"url": _data_url(image)}},
                        ],
                    }
                ],
            },
        )


def _data_url(image: bytes) -> str:
    media = "image/jpeg" if image.startswith(_JPEG) else "image/png"
    return f"data:{media};base64,{base64.b64encode(image).decode('ascii')}"


def _content(response: httpx.Response) -> str:
    body = cast("dict[str, list[dict[str, dict[str, object]]]]", response.json())
    content = body["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        msg = "the model answered with something other than text"
        raise TypeError(msg)
    return content


def _parse(text: str) -> _Answer:
    stripped = text.strip()
    fenced = _FENCE.match(stripped)
    try:
        return _Answer.model_validate(json.loads(fenced.group(1) if fenced else stripped))
    except (ValueError, ValidationError) as exc:
        msg = "the model's answer was not the expected JSON"
        raise ValueError(msg) from exc


def _fields(answer: _Answer) -> tuple[ExtractedField, ...]:
    wanted = fields_for(answer.document_type)
    fields: list[ExtractedField] = []
    for name in FIELD_ORDER:
        if name not in wanted:
            continue
        given = answer.fields.get(name)
        if name == "marks":
            fields.extend(_marks(given))
        else:
            fields.append(_field(name, None, given))
    return tuple(fields)


def _marks(given: object) -> list[ExtractedField]:
    if not isinstance(given, dict) or not given:
        return [_field("marks", None, None)]
    return [_field("marks", str(subject).strip(), mark) for subject, mark in given.items()]


def _field(name: str, subject: str | None, given: object) -> ExtractedField:
    text = "" if given is None or isinstance(given, dict) else str(given).strip()
    if not text:
        return ExtractedField(name, subject, "", 0.0, None, True, "not_extracted")
    reason: ReviewReason = "low_confidence" if is_valid_value(name, text) else "format_invalid"
    return ExtractedField(name, subject, text, None, None, True, reason)
