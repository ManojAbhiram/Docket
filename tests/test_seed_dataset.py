"""The synthetic dataset: counts, determinism, labelled mismatches (REQ-040, 042, 043)."""

import csv
import io

import pytest

from seed.dataset import (
    APPLICATION_COUNT,
    CSV_COLUMNS,
    DOCUMENT_COUNT,
    MISMATCH_COUNT,
    REORDERED_NAME_COUNT,
    Application,
    Dataset,
    DocumentRecord,
    applications_csv,
    build_dataset,
    labels_json,
)


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    return build_dataset(seed=1)


def _application_for(dataset: Dataset, doc: DocumentRecord) -> Application:
    return next(app for app in dataset.applications if app.application_id == doc.application_id)


def _printed_date(app: Application) -> str:
    return app.dob.strftime("%d/%m/%Y")


def test_builds_20_applications_and_30_documents(dataset: Dataset) -> None:
    assert len(dataset.applications) == APPLICATION_COUNT == 20
    assert len(dataset.documents) == DOCUMENT_COUNT == 30


def test_same_seed_gives_the_same_dataset(dataset: Dataset) -> None:
    assert build_dataset(seed=1) == dataset


def test_different_seed_gives_a_different_dataset(dataset: Dataset) -> None:
    assert build_dataset(seed=2) != dataset


def test_all_three_document_types_appear(dataset: Dataset) -> None:
    kinds = {doc.doc_type for doc in dataset.documents}

    assert kinds == {"10th_marksheet", "12th_marksheet", "id_proof"}


def test_four_applications_have_no_documents(dataset: Dataset) -> None:
    with_documents = {doc.application_id for doc in dataset.documents}

    assert len(dataset.applications) - len(with_documents) == 4


def test_application_ids_and_roll_numbers_are_unique_and_marked_synthetic(
    dataset: Dataset,
) -> None:
    ids = [app.application_id for app in dataset.applications]
    rolls = [app.roll_number for app in dataset.applications]

    assert len(set(ids)) == len(ids)
    assert len(set(rolls)) == len(rolls)
    assert all(value.startswith("SYN") for value in ids + rolls)


def test_exactly_eight_documents_carry_a_mismatch(dataset: Dataset) -> None:
    mismatched = [doc for doc in dataset.documents if doc.mismatch_field is not None]

    assert len(mismatched) == MISMATCH_COUNT == 8


def test_a_mismatched_field_differs_from_the_application(dataset: Dataset) -> None:
    docs = dataset.documents
    names = [d for d in docs if d.mismatch_field == "name"]
    dates = [d for d in docs if d.mismatch_field == "dob"]
    rolls = [d for d in docs if d.mismatch_field == "roll_number"]
    marks = [d for d in docs if d.mismatch_field == "marks"]

    assert all(d.printed_name != _application_for(dataset, d).name for d in names)
    assert all(d.printed_dob != _printed_date(_application_for(dataset, d)) for d in dates)
    assert all(d.printed_roll_number != _application_for(dataset, d).roll_number for d in rolls)
    assert all(d.printed_marks != _application_for(dataset, d).marks for d in marks)


def test_a_clean_marksheet_prints_the_application_values(dataset: Dataset) -> None:
    clean = [
        d
        for d in dataset.documents
        if d.mismatch_field is None and not d.name_reordered and d.doc_type != "id_proof"
    ]

    assert clean
    assert all(d.printed_name == _application_for(dataset, d).name for d in clean)
    assert all(d.printed_roll_number == _application_for(dataset, d).roll_number for d in clean)
    assert all(d.printed_marks == _application_for(dataset, d).marks for d in clean)


def test_three_clean_documents_print_the_name_in_reverse_order(dataset: Dataset) -> None:
    reordered = [d for d in dataset.documents if d.name_reordered]
    expected = [
        f"{_application_for(dataset, d).surname} {_application_for(dataset, d).given_name}"
        for d in reordered
    ]

    assert len(reordered) == REORDERED_NAME_COUNT == 3
    assert all(d.mismatch_field is None for d in reordered)
    assert [d.printed_name for d in reordered] == expected


def test_an_id_proof_has_no_marks_roll_number_or_board(dataset: Dataset) -> None:
    id_proofs = [d for d in dataset.documents if d.doc_type == "id_proof"]

    assert id_proofs
    assert all(d.printed_marks is None for d in id_proofs)
    assert all(d.printed_roll_number is None for d in id_proofs)
    assert all(d.printed_board is None for d in id_proofs)


def test_every_document_has_noise_settings_in_range(dataset: Dataset) -> None:
    assert all(0.6 <= d.noise.blur_radius <= 1.6 for d in dataset.documents)
    assert all(-4.0 <= d.noise.skew_degrees <= 4.0 for d in dataset.documents)
    assert all(0.15 <= d.noise.shadow_strength <= 0.45 for d in dataset.documents)


def test_csv_has_the_eight_import_columns_and_one_row_per_application(
    dataset: Dataset,
) -> None:
    rows = list(csv.reader(io.StringIO(applications_csv(dataset))))

    assert tuple(rows[0]) == CSV_COLUMNS
    assert len(rows) == 1 + APPLICATION_COUNT


def test_labels_file_lists_every_document_with_its_expected_outcome(dataset: Dataset) -> None:
    labels = labels_json(dataset)

    assert labels.count('"expect_match"') == DOCUMENT_COUNT
    assert labels.count('"expect_match": false') == MISMATCH_COUNT
