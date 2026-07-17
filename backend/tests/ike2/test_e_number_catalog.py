"""Tests for E-number catalog verification and IKE-2 tier behavior."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.e_number_catalog import (
    build_anchor_facts,
    classify_tier,
    load_catalog,
    normalize_e_code,
)
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.verdict import Verdict
from core.knowledge.ike2.resolver import resolve
from types import SimpleNamespace

_REPO = Path(__file__).resolve().parents[3]
_CATALOG = _REPO / "data" / "e_number_catalog.json"


@pytest.fixture(scope="module")
def catalog_entries():
    return load_catalog(_CATALOG)


def test_catalog_has_330_entries(catalog_entries):
    assert len(catalog_entries) == 330


def test_tier_counts(catalog_entries):
    a = sum(1 for e in catalog_entries if classify_tier(e) == "A")
    b = sum(1 for e in catalog_entries if classify_tier(e) == "B")
    assert a == 280
    assert b == 50


@pytest.mark.parametrize("e_code", ["e100", "e120", "e441", "e471", "e322", "e999"])
def test_e_codes_resolve_in_truth_anchor(e_code, catalog_entries):
    if e_code == "e999":
        assert ta.lookup(e_code) is None
        return
    fact = ta.lookup(e_code)
    assert fact is not None, e_code
    assert fact.canonical_name


def test_tier_b_has_verdict_cap(catalog_entries):
    facts = build_anchor_facts(catalog_entries)
    tier_b_codes = {normalize_e_code(e["e_code"]) for e in catalog_entries if classify_tier(e) == "B"}
    for code in tier_b_codes:
        fact = facts.get(code)
        assert fact is not None
        assert fact.get("verdict_cap") == "WARN" or fact["flags"].get("verdict_cap") == "WARN"


def test_e471_vegan_not_safe():
    fact = ta.lookup("e471")
    assert fact is not None
    resolved = SimpleNamespace(
        group=fact,
        source="truth_anchor",
        trusted=True,
        resolution_layer="L1_truth_anchor",
        status="resolved",
    )
    ci = to_compliance_input(resolved)
    profile = SimpleNamespace(restrictions={"vegan": "preference"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert result.verdict != Verdict.SAFE


def test_e120_vegan_fail():
    fact = ta.lookup("e120")
    assert fact is not None
    resolved = SimpleNamespace(group=fact, source="truth_anchor", trusted=True)
    ci = to_compliance_input(resolved)
    profile = SimpleNamespace(restrictions={"vegan": "preference"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_e322_soy_allergy_uncertain():
    fact = ta.lookup("e322")
    assert fact is not None
    resolved = SimpleNamespace(group=fact, source="truth_anchor", trusted=True)
    ci = to_compliance_input(resolved)
    profile = SimpleNamespace(restrictions={"soy_allergy": "medical"})
    result = evaluate([ci], profile, rules_module.seeded_rules())
    assert result.verdict != Verdict.SAFE
    assert result.verdict in (Verdict.WARN, Verdict.UNCERTAIN)


def test_resolver_e441_resolves():
    r = resolve("e441", None)
    assert r.status == "resolved"
    assert r.resolution_layer == "L1_truth_anchor"


def test_verify_script_zero_errors():
    proc = subprocess.run(
        [sys.executable, str(_REPO / "backend" / "scripts" / "verify_e_number_catalog.py"), "--fail-on-error"],
        capture_output=True,
        text=True,
        cwd=str(_REPO / "backend"),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((_REPO / "data" / "e_number_verification_report.json").read_text())
    assert report["stats"]["error_count"] == 0


def test_all_catalog_e_codes_resolve_l1(catalog_entries):
    for entry in catalog_entries:
        code = normalize_e_code(entry["e_code"])
        assert ta.lookup(code) is not None, code


@pytest.mark.parametrize("variant", ["e100(i)", "e322(ii)", "E 322"])
def test_e_code_subvariants_resolve(variant):
    fact = ta.lookup(normalize_e_code(variant))
    assert fact is not None, variant


def test_generated_artifact_matches_build(catalog_entries):
    built = build_anchor_facts(catalog_entries)
    artifact_path = Path(__file__).resolve().parents[2] / "core" / "knowledge" / "ike2" / "truth_anchor_e_numbers.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert set(built.keys()) == set(artifact.keys())
