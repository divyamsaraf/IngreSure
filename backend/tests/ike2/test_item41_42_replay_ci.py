"""Item 41 + 42 CI: in-memory replay harness (ontology + dumps, no Supabase).

(a) No true hazard flag yields SAFE under its restriction (L2 facts + replayed L3).
(b) After replay, live_true && l2_false drift is empty for verdict-relevant flags.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.bulk_inject import inject, load_dump
from core.knowledge.ike2.etl.load_ontology import load_ontology_records
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.stores import local_ontology as lo
from core.knowledge.ike2.verdict import to_external
from core.normalization.normalizer import normalize_ingredient_key
from tests.ike2.test_etl_bulk_inject import FakeWriter

_REPO = Path(__file__).resolve().parents[3]

ALLERGEN_FLAGS = (
    "fish_source",
    "shellfish_source",
    "dairy_source",
    "egg_source",
    "gluten_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
)

FLAG_TO_RID = {
    "fish_source": "fish_allergy",
    "shellfish_source": "shellfish_allergy",
    "dairy_source": "dairy_free",
    "egg_source": "egg_free",
    "gluten_source": "gluten_free",
    "soy_source": "soy_allergy",
    "sesame_source": "sesame_allergy",
    "peanut_source": "peanut_allergy",
    "tree_nut_source": "tree_nut_allergy",
    "mustard_source": "mustard_allergy",
    "celery_source": "celery_allergy",
    "lupin_source": "lupin_allergy",
    "sulphite_source": "sulfite_sensitive",
}

# Keep CI bounded: ontology seed + allergen-heavy dumps (not every Tier-1 source).
_REPLAY_DUMPS = (
    ("ontology", None),  # load_ontology_records()
    ("usda", _REPO / "data" / "layer1_usda_fdc.json"),
    ("infoods", _REPO / "data" / "layer1_infoods_anfood.json"),
    ("ifct", _REPO / "data" / "layer1_ifct.json"),
)


def _trusted_for_row(row: dict) -> bool:
    unc = row.get("uncertainty_flags") or []
    return not any("inferred" in str(x).lower() for x in unc)


def _eval_flag(row: dict, flag: str) -> str:
    rid = FLAG_TO_RID[flag]
    ci = ComplianceInput(
        canonical_name=row.get("canonical_name") or "",
        flags={f: bool(row.get(f)) for f in BOOL_FLAGS}
        | {
            "uncertainty_flags": list(row.get("uncertainty_flags") or []),
            "animal_species": row.get("animal_species"),
        },
        knowledge_state=row.get("knowledge_state") or "AUTO_CLASSIFIED",
        trusted=_trusted_for_row(row),
        alcohol_role=None,
        verdict_cap=row.get("verdict_cap"),
        trace=False,
        may_contain=False,
    )
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


@pytest.fixture(scope="module")
def replayed_writer() -> FakeWriter:
    """Ontology first, then dumps — same merge order as production inject."""
    w = FakeWriter()
    for source_key, path in _REPLAY_DUMPS:
        if path is None:
            records = list(load_ontology_records())
        else:
            if not path.exists():
                pytest.skip(f"missing dump {path}")
            _src, records = load_dump(str(path))
        # Cap USDA/INFOODS for module speed while keeping shellfish/dairy stress rows.
        if source_key in ("usda", "infoods") and len(records) > 800:
            hot = [r for r in records if any(r.get(f) for f in ALLERGEN_FLAGS)]
            cold = [r for r in records if r not in hot]
            records = (hot + cold)[:800]
        inject(records, source_key, w)
    return w


def test_replay_invariant_no_true_flag_yields_safe(replayed_writer):
    violations = []
    for name, row in replayed_writer.groups.items():
        for flag in ALLERGEN_FLAGS:
            if not row.get(flag):
                continue
            v = _eval_flag(row, flag)
            if v == "SAFE":
                violations.append((name, flag, v, row.get("source")))
    assert violations == [], (
        f"{len(violations)} SAFE-with-true-flag e.g. {violations[:20]}"
    )


def test_replay_l2_drift_live_true_l2_false(replayed_writer):
    """Item 41: after replay, no ontology-named row may hold a true L2 lacks."""
    lo.reset_cache()
    drifted = []
    for name, row in replayed_writer.groups.items():
        norm = normalize_ingredient_key(name)
        fact = lo.lookup(norm)
        if fact is None:
            continue
        l2_flags = dict(fact.flags)
        for flag in ALLERGEN_FLAGS + ("animal_origin",):
            if row.get(flag) and not l2_flags.get(flag):
                drifted.append((name, flag, row.get("source")))
    assert drifted == [], (
        f"{len(drifted)} live_true&&l2_false drifts e.g. {drifted[:30]}"
    )


def test_l2_facts_invariant_no_safe_with_true_flag():
    """L2 path: every ontology.json allergen true must Avoid under its restriction."""
    lo.reset_cache()
    violations = []
    for raw in load_ontology_records():
        mapped, _ = map_record(
            raw, "ontology", default_knowledge_state("ontology")
        )
        for flag in ALLERGEN_FLAGS:
            if not mapped.get(flag):
                continue
            v = _eval_flag(mapped, flag)
            if v == "SAFE":
                violations.append((mapped.get("canonical_name"), flag, v))
    assert violations == [], violations[:20]
