"""Phase D step 5 — canon_facts JSON loader."""

from __future__ import annotations

import json
from pathlib import Path

from service.canon.schema import CanonFacts

DEFAULT_PATH = Path(".local/canon/canon_facts_v3.json")


def load_canon_facts(path: Path = DEFAULT_PATH) -> CanonFacts:
    """canon_facts JSON을 CanonFacts schema로 load."""
    if not path.exists():
        return CanonFacts(
            essences=[],
            characters=[],
            locations=[],
            races=[],
            mechanisms=[],
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return CanonFacts.model_validate(data)
