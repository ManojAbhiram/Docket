"""The four-type synthetic dataset: counts, printed fields, noise range, privacy."""

from collections import Counter

import pytest

from seed.dataset import (
    APPLICATION_COUNT,
    DOC_TYPES,
    DOCUMENT_COUNT,
    FATHER_GIVEN_NAMES,
    GIVEN_NAMES,
    MISMATCH_COUNT,
    REORDERED_NAME_COUNT,
    SURNAMES,
    Application,
    Dataset,
    DocumentRecord,
    build_dataset,
)


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    return build_dataset(seed=1)


def _of_type(dataset: Dataset, doc_type: str) -> list[DocumentRecord]:
    return [d for d in dataset.documents if d.doc_type == doc_type]


def _given_name(name: str) -> str:
    return name.split()[0]


def test_document_types_are_the_four_known_kinds() -> None:
    assert DOC_TYPES == ("10th_marksheet", "12th_marksheet", "id_proof", "transfer_certificate")


def test_builds_30_documents_for_20_applications(dataset: Dataset) -> None:
    assert len(dataset.documents) == DOCUMENT_COUNT == 30
    assert len(dataset.applications) == APPLICATION_COUNT == 20


def test_documents_split_7_8_8_7_across_the_four_types(dataset: Dataset) -> None:
    counts = Counter(doc.doc_type for doc in dataset.documents)

    assert counts == {
        "10th_marksheet": 7,
        "12th_marksheet": 8,
        "id_proof": 8,
        "transfer_certificate": 7,
    }


def test_a_transfer_certificate_prints_name_father_and_dob_only(dataset: Dataset) -> None:
    certificates = _of_type(dataset, "transfer_certificate")

    assert certificates
    assert all(d.printed_name for d in certificates)
    assert all(d.printed_father_name for d in certificates)
    assert all(d.printed_dob for d in certificates)
    assert all(d.printed_board is None for d in certificates)
    assert all(d.printed_roll_number is None for d in certificates)
    assert all(d.printed_marks is None for d in certificates)


def test_a_transfer_certificate_number_starts_with_syntc(dataset: Dataset) -> None:
    certificates = _of_type(dataset, "transfer_certificate")

    assert certificates
    assert all((d.printed_id_number or "").startswith("SYNTC") for d in certificates)


def test_an_id_proof_number_starts_with_synid_and_has_no_father_name(dataset: Dataset) -> None:
    id_proofs = _of_type(dataset, "id_proof")

    assert id_proofs
    assert all((d.printed_id_number or "").startswith("SYNID") for d in id_proofs)
    assert all(d.printed_father_name is None for d in id_proofs)


def test_an_id_proof_mismatch_is_only_ever_name_or_dob(dataset: Dataset) -> None:
    id_proofs = _of_type(dataset, "id_proof")

    assert all(d.mismatch_field in (None, "name", "dob") for d in id_proofs)


def test_a_transfer_certificate_mismatch_is_only_ever_name_or_dob(dataset: Dataset) -> None:
    certificates = _of_type(dataset, "transfer_certificate")

    assert all(d.mismatch_field in (None, "name", "dob") for d in certificates)


def test_every_document_has_a_low_light_level_between_040_and_100(dataset: Dataset) -> None:
    assert all(0.40 <= d.noise.low_light <= 1.00 for d in dataset.documents)


def test_at_least_five_documents_are_dim(dataset: Dataset) -> None:
    dim = [d for d in dataset.documents if d.noise.low_light < 0.7]

    assert len(dim) >= 5


def test_exactly_eight_documents_carry_a_mismatch(dataset: Dataset) -> None:
    mismatched = [d for d in dataset.documents if d.mismatch_field is not None]

    assert len(mismatched) == MISMATCH_COUNT == 8


def test_exactly_three_documents_print_the_name_reordered(dataset: Dataset) -> None:
    reordered = [d for d in dataset.documents if d.name_reordered]

    assert len(reordered) == REORDERED_NAME_COUNT == 3


def test_same_seed_gives_the_same_dataset(dataset: Dataset) -> None:
    assert build_dataset(seed=1) == dataset


def test_application_and_document_ids_are_not_repeated(dataset: Dataset) -> None:
    application_ids = [a.application_id for a in dataset.applications]
    document_ids = [d.document_id for d in dataset.documents]

    assert len(set(application_ids)) == len(application_ids)
    assert len(set(document_ids)) == len(document_ids)


def test_printed_id_numbers_are_not_repeated(dataset: Dataset) -> None:
    numbers = [d.printed_id_number for d in dataset.documents if d.printed_id_number is not None]

    assert numbers
    assert len(set(numbers)) == len(numbers)


def test_every_file_name_is_unique_and_ends_in_png(dataset: Dataset) -> None:
    names = [d.file_name for d in dataset.documents]

    assert len(set(names)) == len(names)
    assert all(name.endswith(".png") for name in names)


def test_every_application_name_comes_from_the_synthetic_pools(dataset: Dataset) -> None:
    apps: tuple[Application, ...] = dataset.applications

    assert all(a.given_name in GIVEN_NAMES for a in apps)
    assert all(a.surname in SURNAMES for a in apps)
    assert all(_given_name(a.father_name) in FATHER_GIVEN_NAMES for a in apps)


def test_every_printed_name_comes_from_the_synthetic_pools(dataset: Dataset) -> None:
    printed = [d for d in dataset.documents if not d.name_reordered]
    fathers = [d.printed_father_name for d in dataset.documents if d.printed_father_name]

    assert all(_given_name(d.printed_name) in GIVEN_NAMES for d in printed)
    assert all(d.printed_name.split()[-1] in SURNAMES for d in printed)
    assert all(_given_name(father) in FATHER_GIVEN_NAMES for father in fathers)


def test_every_roll_number_starts_with_syn(dataset: Dataset) -> None:
    printed = [d.printed_roll_number for d in dataset.documents if d.printed_roll_number]
    applied = [a.roll_number for a in dataset.applications]

    assert printed
    assert all(roll.startswith("SYN") for roll in printed + applied)
