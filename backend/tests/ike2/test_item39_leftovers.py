"""Item 39 leftovers: catalog sesame_source, fibre/fiber identity, ortho shrink."""
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.orthographic_variants import (
    ORTHO_RESTRICTIONS,
    generate_orthographic_pairs,
    reviewed_safe_uncertain,
)
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG
from scripts.shrink_orthographic_baseline import (
    ALLERGY_RESTRICTIONS,
    stale_allergy_entries,
)

_REPO = Path(__file__).resolve().parents[3]
_HAZARD = frozenset(HAZARD_CLASS_TO_FLAG.values())

_CATALOG_PATHS = (
    _REPO / "backend" / "core" / "knowledge" / "ike2" / "etl" / "adapters" / "seeds" / "produce_catalog_seed.json",
    _REPO / "backend" / "core" / "knowledge" / "ike2" / "etl" / "adapters" / "seeds" / "animal_catalog_seed.json",
    _REPO / "data" / "layer1_produce_catalog.json",
    _REPO / "data" / "layer1_animal_catalog.json",
)


def _catalog_rows(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return [r for r in (raw.get("ingredients") or []) if isinstance(r, dict)]


def test_catalog_rows_sesame_source_never_null():
    """Raw catalog JSON must not store sesame_source: null; adapt must emit a bool."""
    seen = 0
    for path in _CATALOG_PATHS:
        assert path.is_file(), path
        source = "produce_catalog" if "produce" in path.name else "animal_catalog"
        for row in _catalog_rows(path):
            seen += 1
            if "sesame_source" in row:
                assert row["sesame_source"] is not None, (path.name, row.get("canonical_name"))
                assert isinstance(row["sesame_source"], bool), (path.name, row.get("canonical_name"))
            mapped, _ = map_record(row, source, default_knowledge_state(source))
            assert mapped.get("sesame_source") in (True, False)
            assert mapped["sesame_source"] is not None
    assert seen >= 5


def test_dietary_fibre_fiber_same_derive_flags():
    """Identity leftover: fibre/fiber must not disagree on hazard derive."""
    a = derive_identity_flags("dietary fibre", {})
    b = derive_identity_flags("dietary fiber", {})
    assert {k: bool(a.get(k)) for k in _HAZARD} == {k: bool(b.get(k)) for k in _HAZARD}


def test_dietary_fibre_fiber_is_orthographic_pair():
    pairs = generate_orthographic_pairs()
    kinds = {kind for _l, _r, kind in pairs}
    assert "fibre/fiber" in kinds
    names = {(left, right) for left, right, _k in pairs}
    assert ("dietary fiber", "dietary fibre") in names or ("dietary fibre", "dietary fiber") in names


def test_shrink_script_identifies_allergy_restrictions_first():
    assert ALLERGY_RESTRICTIONS
    assert ALLERGY_RESTRICTIONS <= set(ORTHO_RESTRICTIONS)
    baseline = reviewed_safe_uncertain()
    allergy = [t for t in baseline if t[2] in ALLERGY_RESTRICTIONS]
    assert len(allergy) <= len(baseline)
    # Helper must be callable on a tiny fixture without touching the live file.
    stale = stale_allergy_entries(
        [
            ("dietary fiber", "dietary fibre", "sesame_allergy"),
            ("dietary fiber", "dietary fibre", "vegan"),
        ],
        still_asymmetric=lambda _a, _b, _r: False,
    )
    assert stale == [("dietary fiber", "dietary fibre", "sesame_allergy")]
