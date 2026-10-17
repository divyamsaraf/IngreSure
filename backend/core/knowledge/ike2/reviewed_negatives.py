"""Reviewed-negatives registry: legal asserted-false (name, flag) pairs.

Invariant: an ``asserted_flags`` entry whose stored value is false is legal
only when ``(normalize(canonical_name), flag)`` is on this registry. The
``>3`` pollution tripwire remains a backstop for mass blocks.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.normalization.normalizer import normalize_ingredient_key

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "ike2_reviewed_negatives.json"
)


@lru_cache(maxsize=1)
def reviewed_negatives() -> frozenset[tuple[str, str]]:
    if not _REGISTRY_PATH.exists():
        return frozenset()
    data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return frozenset(
        (str(row["name"]), str(row["flag"]))
        for row in (data.get("negatives") or [])
        if row.get("name") and row.get("flag")
    )


def asserted_false_allowed(canonical_name: str, flag: str) -> bool:
    norm = normalize_ingredient_key(canonical_name or "")
    return (norm, flag) in reviewed_negatives()


def illegal_asserted_falses(row: dict) -> list[str]:
    """Return asserted-false flag names not on the reviewed-negatives registry."""
    name = row.get("canonical_name") or ""
    out = []
    for flag in row.get("asserted_flags") or []:
        if row.get(flag):
            continue
        if not asserted_false_allowed(name, flag):
            out.append(flag)
    return out
