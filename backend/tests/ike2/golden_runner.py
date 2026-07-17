"""Shared helpers for IKE-2 golden corpus tests."""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.input_layer import parse_atoms
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external

CORPUS = pathlib.Path(__file__).parent / "golden" / "corpus.jsonl"


def load_corpus() -> list[dict]:
    cases = []
    for line in CORPUS.read_text().splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def safe_resolve(name: str, region):
    try:
        return resolve(name, region)
    except Exception:
        return SimpleNamespace(group=None, trusted=False, status="uncertain")


def run_case(case: dict) -> str:
    inputs = []
    for atom in parse_atoms(case["raw_input"]):
        resolved = safe_resolve(atom.name, case.get("region"))
        inputs.append(
            to_compliance_input(resolved, trace=atom.trace, may_contain=atom.may_contain)
        )
    raw_profile = case["profile"]
    restrictions = raw_profile.get("restrictions", raw_profile)
    profile = SimpleNamespace(restrictions=restrictions)
    return to_external(evaluate(inputs, profile, rules=rules_module.seeded_rules()))


def run_case_full(case: dict):
    """Return compliance inputs, result, and external verdict for pipeline tests."""
    inputs = []
    resolved_rows = []
    for atom in parse_atoms(case["raw_input"]):
        resolved = safe_resolve(atom.name, case.get("region"))
        resolved_rows.append(resolved)
        inputs.append(
            to_compliance_input(resolved, trace=atom.trace, may_contain=atom.may_contain)
        )
    raw_profile = case["profile"]
    restrictions = raw_profile.get("restrictions", raw_profile)
    profile = SimpleNamespace(restrictions=restrictions)
    result = evaluate(inputs, profile, rules=rules_module.seeded_rules())
    external = to_external(result.verdict)
    return resolved_rows, result, external, profile
