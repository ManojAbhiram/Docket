"""The opt-in OpenRouter Vision reader (ADR-0015).

One request per page to a free vision model. Nothing here is trusted: the answer is parsed, its
shape checked, and every field is marked for review because a model gives no confidence and no box.
The provider's own message is never kept, because it can echo a value from the page (REQ-044).
"""

import base64
import json
import re
import time
from collections.abc import Callable
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
# A 600-token answer needs only a few KiB. Leave room for provider metadata, then bound the
# entire envelope independently of the model's requested token limit.
MAX_RESPONSE_BYTES = 64 * 1024
_TOO_MANY_REQUESTS = 429

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


class VisionError(Exception):
    """Why Vision could not answer. Only the class travels onward, never a provider message."""


class VisionTimeoutError(VisionError):
    """The provider did not answer in time."""


class VisionRateLimitedError(VisionError):
    """The provider said the free tier is busy or used up (HTTP 429, or the same in the body)."""


class VisionUpstreamError(VisionError):
    """The provider failed or could not be reached."""


class VisionBadAnswerError(VisionError):
    """The provider answered, but not with a usable document."""


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
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._key = api_key
        self._model = model
        self._ledger = ledger
        self._cap = cap
        self._deadline_seconds = timeout_seconds
        self._clock = clock
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

    @property
    def deadline_seconds(self) -> float:
        """The most seconds one call may take in total, read by the worker for its own cutoff."""
        return self._deadline_seconds

    def close(self) -> None:
        self._client.close()

    def _ask(self, image: bytes) -> ProcessedDocument:
        try:
            response = self._post(image)
        except httpx.TimeoutException as exc:
            raise VisionTimeoutError from exc
        except httpx.HTTPStatusError as exc:
            raise _for_status(exc.response.status_code) from exc
        except httpx.TransportError as exc:
            raise VisionUpstreamError from exc
        answer = _parse(_content(response))
        return ProcessedDocument(
            doc_type=answer.document_type,
            fields=_fields(answer),
            engine=ENGINE_NAME,
        )

    def _post(self, image: bytes) -> httpx.Response:
        """One request that must finish within the deadline in total, not per read.

        httpx times out each read, and a provider that trickles keep-alive bytes resets that
        timer, so the whole call is held to a deadline checked as each piece arrives.
        """
        deadline = self._clock() + self._deadline_seconds
        with self._client.stream(
            "POST",
            ENDPOINT,
            headers={"Authorization": f"Bearer {self._key}", "Accept-Encoding": "identity"},
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
        ) as response:
            response.raise_for_status()
            # Refuse servers ignoring identity before HTTPX can inflate compressed chunks.
            # This small structured answer needs no compression; refusal uses local OCR fallback.
            if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
                raise VisionBadAnswerError
            body = bytearray()
            # Preserve transport yields: coalescing tiny keep-alive pieces can hide the deadline.
            # No admitted piece may exceed the remaining response budget.
            for piece in response.iter_bytes():
                if self._clock() > deadline:
                    raise VisionTimeoutError
                if len(body) + len(piece) > MAX_RESPONSE_BYTES:
                    raise VisionBadAnswerError
                body += piece
            return httpx.Response(response.status_code, content=bytes(body))


def _data_url(image: bytes) -> str:
    media = "image/jpeg" if image.startswith(_JPEG) else "image/png"
    return f"data:{media};base64,{base64.b64encode(image).decode('ascii')}"


def _for_status(status: int) -> VisionError:
    return VisionRateLimitedError() if status == _TOO_MANY_REQUESTS else VisionUpstreamError()


def _content(response: httpx.Response) -> str:
    """The model's text. OpenRouter can answer 200 with an error object instead of choices."""
    try:
        body = cast("dict[str, object]", response.json())
        if "error" in body:
            error = cast("dict[str, object]", body["error"])
            raise _for_status(int(cast("int", error.get("code", 0))))
        choices = cast("list[dict[str, dict[str, object]]]", body["choices"])
        content = choices[0]["message"]["content"]
    except VisionError:
        raise
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise VisionBadAnswerError from exc
    if not isinstance(content, str):
        raise VisionBadAnswerError
    return content


def _parse(text: str) -> _Answer:
    stripped = text.strip()
    fenced = _FENCE.match(stripped)
    try:
        return _Answer.model_validate(json.loads(fenced.group(1) if fenced else stripped))
    except (ValueError, ValidationError) as exc:
        raise VisionBadAnswerError from exc


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
