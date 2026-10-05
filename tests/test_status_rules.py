"""Each application gets exactly one status, set from evidence (US-00-005, REQ-017 to REQ-020).

Every test here fails until `app/domain/status.py` exists. The status function is pure: it reads
what each document and field looked like and returns one of three words.
"""

import pytest

from app.domain.status import (
    DocumentFacts,
    FieldFacts,
    VerificationNotAllowedError,
    assert_can_verify,
    compute_status,
)

MATCH = FieldFacts(match=True)
MISMATCH = FieldFacts(match=False)
WEAK = FieldFacts(match=True, needs_review=True)
SKIPPED = FieldFacts(match=None)


def read(doc_type: str, *fields: FieldFacts) -> DocumentFacts:
    return DocumentFacts(doc_type=doc_type, state="read", fields=fields)


def complete_and_matching() -> list[DocumentFacts]:
    return [
        read("10th_marksheet", MATCH, MATCH),
        read("12th_marksheet", MATCH, MATCH),
        read("id_proof", MATCH, SKIPPED),
    ]


def test_every_required_document_present_and_every_field_matching_is_verified() -> None:
    assert compute_status(complete_and_matching()) == "verified"


def test_a_skipped_field_is_not_counted_as_a_mismatch() -> None:
    assert compute_status(
        [read(t, SKIPPED) for t in ("10th_marksheet", "12th_marksheet", "id_proof")]
    ) == ("verified")


def test_a_mismatching_field_sends_the_application_to_needs_review() -> None:
    documents = complete_and_matching()
    documents[0] = read("10th_marksheet", MATCH, MISMATCH)

    assert compute_status(documents) == "needs_review"


def test_a_low_confidence_field_sends_the_application_to_needs_review() -> None:
    documents = complete_and_matching()
    documents[1] = read("12th_marksheet", WEAK)

    assert compute_status(documents) == "needs_review"


def test_a_document_that_failed_to_read_is_a_persons_job_not_a_missing_upload() -> None:
    documents = complete_and_matching()
    documents[2] = DocumentFacts(doc_type=None, state="failed")

    assert compute_status(documents) == "needs_review"


def test_a_document_of_unknown_type_sends_the_application_to_needs_review() -> None:
    documents = complete_and_matching()
    documents.append(read("unknown", SKIPPED))

    assert compute_status(documents) == "needs_review"


def test_a_missing_required_document_type_is_missing_documents() -> None:
    documents = [read("10th_marksheet", MATCH), read("id_proof", MATCH)]

    assert compute_status(documents) == "missing_documents"


def test_no_documents_at_all_is_missing_documents() -> None:
    assert compute_status([]) == "missing_documents"


def test_a_document_still_being_read_cannot_make_the_application_verified() -> None:
    documents = complete_and_matching()
    documents[0] = DocumentFacts(doc_type=None, state="processing")

    assert compute_status(documents) == "missing_documents"


def test_needs_review_beats_missing_documents() -> None:
    documents = [DocumentFacts(doc_type=None, state="failed"), read("id_proof", MATCH)]

    assert compute_status(documents) == "needs_review"


def test_an_approval_makes_a_flagged_application_verified() -> None:
    documents = complete_and_matching()
    documents[0] = read("10th_marksheet", MATCH, MISMATCH)

    assert compute_status(documents, approved=True) == "verified"


def test_an_approval_cannot_stand_in_for_a_missing_required_document() -> None:
    documents = [read("10th_marksheet", MISMATCH), read("id_proof", MATCH)]

    assert compute_status(documents, approved=True) == "missing_documents"


def test_a_direct_request_for_verified_is_refused_without_a_match_or_a_decision() -> None:
    documents = complete_and_matching()
    documents[0] = read("10th_marksheet", MISMATCH)

    with pytest.raises(VerificationNotAllowedError):
        assert_can_verify(documents, approved=False)


def test_a_direct_request_for_verified_is_allowed_after_an_approval() -> None:
    documents = complete_and_matching()
    documents[0] = read("10th_marksheet", MISMATCH)

    assert_can_verify(documents, approved=True)


@pytest.mark.parametrize(
    "documents",
    [[], complete_and_matching(), [DocumentFacts(doc_type=None, state="failed")]],
)
def test_the_status_is_always_one_of_the_three(documents: list[DocumentFacts]) -> None:
    assert compute_status(documents) in {"verified", "needs_review", "missing_documents"}
