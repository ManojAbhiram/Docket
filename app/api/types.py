"""Value sets the API shares between its schemas."""

from typing import Literal

DocumentType = Literal[
    "10th_marksheet", "12th_marksheet", "id_proof", "transfer_certificate", "unknown"
]
