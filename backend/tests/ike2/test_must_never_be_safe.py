"""Hard CI gate: zero FALSE-SAFE on the must_never_be_safe golden corpus.

Any SAFE verdict on these cases is a merge blocker. Tier-M (medical) and Tier-R
(religious) failures are equally blocking — a wrong Safe is a trust violation.

Also stresses degraded Tier-2/Tier-3 rows for curated canons so under-flagged
DB/ontology data cannot silently clear medical/religious restrictions.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace

import pytest

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import ResolvedIngredient
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology
from core.knowledge.ike2.truth_anchor import TruthAnchorFact
from core.knowledge.ike2.verdict import to_external
from tests.ike2.golden_runner import run_case

CORPUS = pathlib.Path(__file__).parent / "golden" / "must_never_be_safe.jsonl"
LEGACY = pathlib.Path(__file__).parent / "golden" / "corpus.jsonl"


def _load(path: pathlib.Path) -> list[dict]:
    cases = []
    for line in path.read_text().splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def _must_never_cases() -> list[dict]:
    cases = [c for c in _load(CORPUS) if c.get("must_not_be_safe", True)]
    # Include legacy corpus entries marked must_not_be_safe
    for c in _load(LEGACY):
        if c.get("must_not_be_safe") is True:
            cases.append(c)
    return cases


def test_must_never_be_safe_corpus_nonempty():
    cases = _must_never_cases()
    assert len(cases) >= 80, f"corpus too small: {len(cases)}"
    tiers = {c.get("severity_tier") for c in _load(CORPUS)}
    assert {"M", "R", "P"} <= tiers


def test_zero_false_safe_on_must_never_be_safe_corpus():
    """P0 gate: no case in the corpus may resolve to SAFE."""
    false_safes = []
    for case in _must_never_cases():
        got = run_case(case)
        if got == "SAFE":
            false_safes.append(
                {
                    "raw": case["raw_input"],
                    "restrictions": case["profile"].get("restrictions"),
                    "tier": case.get("severity_tier"),
                    "class": case.get("ambiguity_class"),
                    "rationale": case.get("rationale"),
                }
            )
    assert false_safes == [], f"FALSE-SAFE regressions ({len(false_safes)}):\n{false_safes}"


def test_medical_tier_never_safe_even_more_strict():
    """Tier-M cases must be NOT_SAFE or UNCERTAIN — never SAFE."""
    medical = [c for c in _load(CORPUS) if c.get("severity_tier") == "M"]
    assert medical, "missing Tier-M cases"
    bad = []
    for case in medical:
        got = run_case(case)
        if got == "SAFE":
            bad.append((case["raw_input"], case["profile"], got))
    assert bad == [], f"Tier-M FALSE-SAFE: {bad}"


def _degraded_fact(atom: str) -> TruthAnchorFact | None:
    """Simulate under-flagged Tier-2/DB row for a curated canon."""
    t1 = ta.lookup(atom)
    t2 = local_ontology.lookup(atom)
    if t1 is None:
        return None
    base = dict(t2.flags) if t2 is not None else {}
    # Strip safety bits that ETL/DB historically under-flagged
    for k in (
        "fish_source",
        "shellfish_source",
        "peanut_source",
        "tree_nut_source",
        "soy_source",
        "egg_source",
        "dairy_source",
        "insect_derived",
        "bee_product",
        "animal_origin",
    ):
        if t1.flags.get(k):
            base[k] = False
    # Stale honey shape
    if atom == "honey":
        base["animal_origin"] = True
        base["insect_derived"] = True
        base.pop("bee_product", None)
        base["bee_product"] = False
    return TruthAnchorFact(
        canonical_name=t1.canonical_name,
        flags=base,
        knowledge_state="DISCOVERED",
    )


@pytest.mark.parametrize(
    "atom,restriction",
    [
        ("tuna", "fish_allergy"),
        ("shrimp", "shellfish_allergy"),
        ("gelatin", "fish_allergy"),
        ("peanut", "peanut_allergy"),
        ("carmine", "hindu_vegetarian"),
        ("honey", "vegan"),
        ("honey", "jain"),
    ],
)
def test_degraded_tier_rows_never_false_safe(atom, restriction):
    """Under-flagged DISCOVERED DB rows must not clear curated safety canons."""
    fact = _degraded_fact(atom)
    assert fact is not None, atom
    ri = ResolvedIngredient(
        group=fact,
        source="db",
        confidence_band="high",
        trusted=True,
        resolution_layer="L3_degraded",
        status="resolved",
    )
    ci = to_compliance_input(ri, query_atom=atom)
    severity = "medical" if restriction.endswith("_allergy") or restriction == "vegan" else "preference"
    got = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={restriction: severity}),
            rules_module.seeded_rules(),
        ).verdict
    )
    assert got != "SAFE", (atom, restriction, got, fact.flags)
