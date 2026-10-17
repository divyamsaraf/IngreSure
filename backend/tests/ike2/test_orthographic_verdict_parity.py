"""Orthographic spelling pairs must not disagree on firm SAFE vs NOT_SAFE.

Gates every pair the alias-universe scan generates (not a curated shortlist).
SAFE ↔ UNCERTAIN asymmetries are grandfathered in
``orthographic_safe_uncertain_baseline.json`` (ratchet, not a written review).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.orthographic_variants import (
    ORTHO_RESTRICTIONS,
    generate_orthographic_pairs,
    reviewed_safe_uncertain,
)
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.normalization.normalizer import normalize_ingredient_key


def _verdict(name: str, restriction: str) -> str:
    r = resolve(name, None)
    ci = to_compliance_input(r, query_atom=name)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={restriction: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


def _pair_cases():
    cases = []
    for left, right, _kind in generate_orthographic_pairs():
        for rid in ORTHO_RESTRICTIONS:
            cases.append((left, right, rid))
    return cases


@pytest.mark.parametrize("left,right,restriction", _pair_cases())
def test_orthographic_pair_no_safe_vs_not_safe(left, right, restriction):
    assert normalize_ingredient_key(left) != normalize_ingredient_key(right)
    vl = _verdict(left, restriction)
    vr = _verdict(right, restriction)
    firm = {vl, vr}
    assert firm != {"SAFE", "NOT_SAFE"}, (
        f"{left!r}={vl} vs {right!r}={vr} under {restriction}"
    )
    if firm == {"SAFE", "UNCERTAIN"}:
        key = tuple(sorted((left, right)) + [restriction])
        assert key in reviewed_safe_uncertain(), (
            f"unreviewed SAFE/UNCERTAIN asymmetry: {left!r}={vl} vs {right!r}={vr} "
            f"under {restriction}"
        )


def test_scan_generates_multiple_pairs():
    pairs = generate_orthographic_pairs()
    assert len(pairs) >= 20
