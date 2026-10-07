"""Document subsets for the engine comparison, chosen by rule so no one picks by hand."""

from collections.abc import Sequence

from seed.dataset import DocumentRecord

COMPARISON_SIZE = 10


def compare_ten(docs: Sequence[DocumentRecord]) -> list[DocumentRecord]:
    """Ten documents, one per type in turn, in document id order: stable and covers every type."""
    queues: dict[str, list[DocumentRecord]] = {}
    for doc in sorted(docs, key=lambda d: d.document_id):
        queues.setdefault(doc.doc_type, []).append(doc)
    picked: list[DocumentRecord] = []
    while len(picked) < COMPARISON_SIZE and any(queues.values()):
        for doc_type in sorted(queues):
            if queues[doc_type] and len(picked) < COMPARISON_SIZE:
                picked.append(queues[doc_type].pop(0))
    return picked


def noisiest(docs: Sequence[DocumentRecord], count: int = 10) -> list[DocumentRecord]:
    """The `count` documents with the most blur, skew and shadow, from the stored noise values."""
    ranked = sorted(docs, key=lambda d: (-noise_level(d), d.document_id))
    return ranked[:count]


def noise_level(doc: DocumentRecord) -> float:
    """Blur radius plus skew in 5 degree units plus shadow strength."""
    noise = doc.noise
    return noise.blur_radius + abs(noise.skew_degrees) / 5 + noise.shadow_strength
