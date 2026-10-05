"""Deterministic synthetic dataset: 20 applications, 30 documents, labelled mismatches.

Every name, date, roll number and mark is generated here. Nothing is read from a
real record (REQ-043). The data layer is plain Python so it runs without an image
library; rendering lives in `seed.render`.
"""

import csv
import dataclasses
import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

type DocType = Literal["10th_marksheet", "12th_marksheet", "id_proof"]
type MismatchField = Literal["name", "dob", "roll_number", "marks"]

DOC_TYPES: tuple[DocType, DocType, DocType] = ("10th_marksheet", "12th_marksheet", "id_proof")
APPLICATION_COUNT = 20
DOCUMENT_COUNT = 30
MISMATCH_COUNT = 8
REORDERED_NAME_COUNT = 3
ID_PREFIX = "SYN"

CSV_COLUMNS = (
    "application_id",
    "name",
    "father_name",
    "date_of_birth",
    "board",
    "roll_number",
    "marks_by_subject",
    "category",
)

GIVEN_NAMES = (
    "Aarav", "Diya", "Kabir", "Meera", "Rohan", "Sanya", "Vivaan", "Ishita", "Arjun", "Nisha",
    "Tanvi", "Karan", "Pooja", "Ritesh", "Anjali", "Dev", "Latha", "Imran", "Farah", "Joseph",
)  # fmt: skip
FATHER_GIVEN_NAMES = (
    "Suresh", "Ramesh", "Anil", "Mahesh", "Vijay", "Prakash", "Naveen", "Salim", "Thomas", "Gopal",
)  # fmt: skip
SURNAMES = ("Rao", "Nair", "Sharma", "Iyer", "Khan", "Patel", "Reddy", "Das", "Menon", "Gupta")
BOARDS = ("CBSE", "ICSE", "Karnataka State Board", "Maharashtra State Board")
CATEGORIES = ("General", "OBC", "SC", "ST")
SUBJECTS = ("English", "Hindi", "Mathematics", "Science", "Social Science")

_MASK = (1 << 64) - 1
_MISMATCH_CYCLE: tuple[MismatchField, ...] = ("name", "dob", "roll_number", "marks")
_MARKSHEET_FIELDS: frozenset[MismatchField] = frozenset({"name", "dob", "roll_number", "marks"})
_ID_PROOF_FIELDS: frozenset[MismatchField] = frozenset({"name", "dob"})


class SeededRng:
    """SplitMix64 generator: the same seed gives the same sequence on every machine."""

    def __init__(self, seed: int) -> None:
        self._state = seed & _MASK

    def _next(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, bound: int) -> int:
        """An integer in [0, bound)."""
        return self._next() % bound

    def between(self, low: int, high: int) -> int:
        """An integer in [low, high], both inclusive."""
        return low + self.below(high - low + 1)

    def uniform(self, low: float, high: float) -> float:
        """A float in [low, high]."""
        return low + (self._next() / _MASK) * (high - low)

    def pick[T](self, items: Sequence[T]) -> T:
        return items[self.below(len(items))]

    def sample[T](self, items: Sequence[T], count: int) -> list[T]:
        """`count` distinct items, in random order."""
        pool = list(items)
        return [pool.pop(self.below(len(pool))) for _ in range(count)]


@dataclass(frozen=True)
class Application:
    application_id: str
    given_name: str
    surname: str
    father_name: str
    dob: date
    board: str
    roll_number: str
    marks: dict[str, int]
    category: str

    @property
    def name(self) -> str:
        return f"{self.given_name} {self.surname}"


@dataclass(frozen=True)
class NoiseSpec:
    """Photo noise applied when a document is rendered to PNG."""

    blur_radius: float
    skew_degrees: float
    shadow_strength: float


@dataclass(frozen=True)
class DocumentRecord:
    """One synthetic document and what it is supposed to show.

    `printed_*` is what appears on the page. A field the document type does not
    carry is None. `mismatch_field` names the one field deliberately changed from
    the application; `name_reordered` swaps given name and surname, which should
    still match under token-sorted comparison.
    """

    document_id: str
    application_id: str
    doc_type: DocType
    printed_name: str
    printed_father_name: str | None
    printed_dob: str
    printed_board: str | None
    printed_roll_number: str | None
    printed_marks: dict[str, int] | None
    printed_id_number: str | None
    mismatch_field: MismatchField | None
    name_reordered: bool
    noise: NoiseSpec

    @property
    def expect_match(self) -> bool:
        return self.mismatch_field is None

    @property
    def file_name(self) -> str:
        return f"{self.application_id}_{self.doc_type}.png"


@dataclass(frozen=True)
class Dataset:
    seed: int
    applications: tuple[Application, ...]
    documents: tuple[DocumentRecord, ...]


def build_dataset(seed: int = 20261005) -> Dataset:
    """Build the full synthetic set. Same seed, same dataset."""
    rng = SeededRng(seed)
    applications = _build_applications(rng)
    plan = _document_plan()
    mismatches = _assign_mismatches(rng, plan)
    reordered = _assign_reordered(rng, mismatches)
    documents = tuple(
        _build_document(rng, index, applications[app_index], doc_type, mismatches.get(index),
                        index in reordered)
        for index, (app_index, doc_type) in enumerate(plan)
    )  # fmt: skip
    return Dataset(seed=seed, applications=applications, documents=documents)


def applications_csv(dataset: Dataset) -> str:
    """The applications as the CSV staff would import (REQ-001, REQ-002)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for app in dataset.applications:
        writer.writerow(
            (
                app.application_id,
                app.name,
                app.father_name,
                app.dob.isoformat(),
                app.board,
                app.roll_number,
                json.dumps(app.marks, sort_keys=True),
                app.category,
            )
        )
    return buffer.getvalue()


def labels_json(dataset: Dataset) -> str:
    """Ground truth for the eval: every document, its printed values and its mismatch."""
    payload = {
        "seed": dataset.seed,
        "applications": [dataclasses.asdict(app) for app in dataset.applications],
        "documents": [
            {**dataclasses.asdict(doc), "expect_match": doc.expect_match, "file": doc.file_name}
            for doc in dataset.documents
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


def _build_applications(rng: SeededRng) -> tuple[Application, ...]:
    combos = [(given, surname) for given in GIVEN_NAMES for surname in SURNAMES]
    names = rng.sample(combos, APPLICATION_COUNT)
    used_rolls: set[str] = set()
    applications: list[Application] = []
    for index, (given, surname) in enumerate(names):
        roll = _new_roll_number(rng, used_rolls)
        used_rolls.add(roll)
        applications.append(
            Application(
                application_id=f"{ID_PREFIX}-APP-{index + 1:03d}",
                given_name=given,
                surname=surname,
                father_name=f"{rng.pick(FATHER_GIVEN_NAMES)} {surname}",
                dob=date(2006, 1, 1) + timedelta(days=rng.below(1095)),
                board=rng.pick(BOARDS),
                roll_number=roll,
                marks={subject: rng.between(35, 98) for subject in SUBJECTS},
                category=rng.pick(CATEGORIES),
            )
        )
    return tuple(applications)


def _new_roll_number(rng: SeededRng, used: set[str]) -> str:
    while True:
        roll = ID_PREFIX + "".join(str(rng.below(10)) for _ in range(7))
        if roll not in used:
            return roll


def _document_plan() -> list[tuple[int, DocType]]:
    """Which application gets which documents: 4 apps with 3, 6 with 2, 6 with 1, 4 with none."""
    plan: list[tuple[int, DocType]] = []
    for app_index in range(APPLICATION_COUNT):
        if app_index < 4:
            count = 3
        elif app_index < 10:
            count = 2
        elif app_index < 16:
            count = 1
        else:
            count = 0
        plan.extend((app_index, DOC_TYPES[(app_index + offset) % 3]) for offset in range(count))
    return plan


def _assign_mismatches(rng: SeededRng, plan: list[tuple[int, DocType]]) -> dict[int, MismatchField]:
    chosen = rng.sample(range(len(plan)), MISMATCH_COUNT)
    assigned: dict[int, MismatchField] = {}
    for order, doc_index in enumerate(chosen):
        allowed = _ID_PROOF_FIELDS if plan[doc_index][1] == "id_proof" else _MARKSHEET_FIELDS
        candidates = [_MISMATCH_CYCLE[(order + shift) % 4] for shift in range(4)]
        assigned[doc_index] = next(kind for kind in candidates if kind in allowed)
    return assigned


def _assign_reordered(rng: SeededRng, mismatches: dict[int, MismatchField]) -> set[int]:
    clean = [index for index in range(DOCUMENT_COUNT) if index not in mismatches]
    return set(rng.sample(clean, REORDERED_NAME_COUNT))


def _build_document(
    rng: SeededRng,
    index: int,
    app: Application,
    doc_type: DocType,
    mismatch: MismatchField | None,
    reordered: bool,
) -> DocumentRecord:
    name = f"{app.surname} {app.given_name}" if reordered else app.name
    dob = app.dob
    roll = app.roll_number
    marks = dict(app.marks)
    if mismatch == "name":
        other = rng.pick([given for given in GIVEN_NAMES if given != app.given_name])
        name = f"{other} {app.surname}"
    elif mismatch == "dob":
        dob = app.dob + timedelta(days=rng.between(1, 27))
    elif mismatch == "roll_number":
        roll = _change_one_digit(rng, app.roll_number)
    elif mismatch == "marks":
        subject = rng.pick(SUBJECTS)
        marks[subject] = _change_mark(rng, app.marks[subject])
    is_marksheet = doc_type != "id_proof"
    return DocumentRecord(
        document_id=f"{ID_PREFIX}-DOC-{index + 1:03d}",
        application_id=app.application_id,
        doc_type=doc_type,
        printed_name=name,
        printed_father_name=app.father_name if is_marksheet else None,
        printed_dob=dob.strftime("%d/%m/%Y"),
        printed_board=app.board if is_marksheet else None,
        printed_roll_number=roll if is_marksheet else None,
        printed_marks=marks if is_marksheet else None,
        printed_id_number=None if is_marksheet else f"{ID_PREFIX}ID{rng.between(10**7, 10**8 - 1)}",
        mismatch_field=mismatch,
        name_reordered=reordered,
        noise=NoiseSpec(
            blur_radius=round(rng.uniform(0.6, 1.6), 2),
            skew_degrees=round(rng.uniform(-4.0, 4.0), 2),
            shadow_strength=round(rng.uniform(0.15, 0.45), 2),
        ),
    )


def _change_one_digit(rng: SeededRng, roll: str) -> str:
    position = rng.between(len(ID_PREFIX), len(roll) - 1)
    new_digit = str((int(roll[position]) + rng.between(1, 9)) % 10)
    return roll[:position] + new_digit + roll[position + 1 :]


def _change_mark(rng: SeededRng, mark: int) -> int:
    delta = rng.between(1, 5)
    return mark + delta if mark + delta <= 100 else mark - delta
