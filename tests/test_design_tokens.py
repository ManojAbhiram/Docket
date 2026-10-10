"""Regenerating the design must preserve its reviewed, checked-in color contract."""

import json
from pathlib import Path

from scripts.make_tokens import tokens


def test_regenerating_tokens_preserves_the_reviewed_design() -> None:
    expected: object = json.loads(
        (Path(__file__).parents[1] / "docs/design/tokens.json").read_text(encoding="utf-8")
    )

    assert tokens() == expected
