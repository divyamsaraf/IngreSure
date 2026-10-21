"""English pantry gaps: class promotions through the reviewed (true-only) path."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.validate import validate_rows
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores.local_ontology import reset_cache
from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache
from core.knowledge.ike2.verdict import to_external

_REPO = Path(__file__).resolve().parents[2]
_PROMOS = _REPO / "data" / "lexicon" / "reviewed_class_promotions.json"

REQUIRED = (
    "milk solids",
    "cocoa solids",
    "palmolein",
    "iodised salt",
    "vitamin a palmitate",
    "vitamin b12",
    "vitamin d2",
    "thiamin mononitrate",
)


def _fresh():
    cache.clear()
    reset_cache()
    reset_variant_alias_cache()


def _verdict(atom: str, rid: str) -> str:
    ci = to_compliance_input(resolve(atom, None), query_atom=atom)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


def test_promotions_file_is_true_only_reviewed():
    data = json.loads(_PROMOS.read_text(encoding="utf-8"))
    names = {p["canonical_name"].lower() for p in data["promotions"]}
    assert set(REQUIRED) <= names
    for promo in data["promotions"]:
        raw = {f: False for f in BOOL_FLAGS}
        raw.update({k: promo[k] for k in BOOL_FLAGS if k in promo})
        raw["canonical_name"] = promo["canonical_name"]
        raw["aliases"] = list(promo.get("aliases") or [])
        raw["asserted_flags"] = list(promo.get("asserted_flags") or [])
        row, _ = map_record(raw, "ontology", "AUTO_CLASSIFIED")
        for flag in row.get("asserted_flags") or []:
            assert row.get(flag) is True, (promo["canonical_name"], flag)
        ok, rejects = validate_rows([row])
        assert rejects == [], (promo["canonical_name"], rejects)
        assert ok


def test_milk_solids_resolves_and_avoids_dairy_free():
    _fresh()
    r = resolve("milk solids", None)
    assert r.status == "resolved"
    assert derive_identity_flags("milk solids").get("dairy_source") is True
    assert _verdict("milk solids", "dairy_free") == "NOT_SAFE"


def test_clearance_gaps_resolve_without_invented_dairy():
    _fresh()
    for atom in ("cocoa solids", "palmolein", "iodised salt", "vitamin b12"):
        r = resolve(atom, None)
        assert r.status == "resolved", atom
        assert derive_identity_flags(atom).get("dairy_source") is not True, atom
        assert _verdict(atom, "dairy_free") == "SAFE", atom


def test_vitamin_forms_resolve():
    _fresh()
    for atom in ("vitamin a palmitate", "vitamin d2", "thiamin mononitrate"):
        r = resolve(atom, None)
        assert r.status == "resolved", atom
        assert r.trusted is True, atom
