"""Name the type of a document from the title printed at the top of it (US-00-003, REQ-009)."""

import re
from collections.abc import Sequence

from app.gateway import OcrWord

_CLASS_X = re.compile(r"\bclass x\b")


def classify(words: Sequence[OcrWord]) -> str:
    """One of the four document types, or `unknown`, which sends the application to review."""
    text = " ".join(" ".join(word.text.split()) for word in words).casefold()
    if "class xii" in text:
        return "12th_marksheet"
    if _CLASS_X.search(text):
        return "10th_marksheet"
    if "identity card" in text:
        return "id_proof"
    if "transfer certificate" in text:
        return "transfer_certificate"
    return "unknown"
