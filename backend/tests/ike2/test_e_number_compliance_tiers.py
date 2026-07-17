"""Compliance tier tests for ambiguous E-number additives (Tier B)."""

from types import SimpleNamespace

import pytest

from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict


def _eval_e_code(code: str, restriction: str, severity: str = "preference"):
    fact = ta.lookup(code)
    assert fact is not None, code
    ci = to_compliance_input(SimpleNamespace(group=fact, trusted=True))
    profile = SimpleNamespace(restrictions={restriction: severity})
    return evaluate([ci], profile, rules_module.seeded_rules())


@pytest.mark.parametrize(
    "code,restriction",
    [
        ("e471", "vegan"),
        ("e471", "halal"),
        ("e322", "vegan"),
        ("e101", "vegan"),
        ("e910", "vegan"),
    ],
)
def test_tier_b_never_firm_safe(code, restriction):
    result = _eval_e_code(code, restriction)
    assert result.verdict != Verdict.SAFE


def test_e120_vegan_is_fail():
    assert _eval_e_code("e120", "vegan", "medical").verdict == Verdict.FAIL


def test_e441_vegan_is_fail():
    assert _eval_e_code("e441", "vegan", "medical").verdict == Verdict.FAIL


def test_e100_vegan_can_be_safe():
    result = _eval_e_code("e100", "vegan")
    assert result.verdict == Verdict.SAFE
