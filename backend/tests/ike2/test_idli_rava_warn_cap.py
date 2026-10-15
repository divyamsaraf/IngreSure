"""idli rava: WARN cap, not a firm gluten-free claim."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external


def test_derive_does_not_set_gluten_on_idli_or_rice_rava():
    for name in ("idli rava", "rice rava", "rice sooji"):
        assert derive_identity_flags(name, {}).get("gluten_source") is not True


def test_wheat_rava_family_still_gluten():
    for name in ("rava", "sooji", "suji", "upma rava"):
        assert derive_identity_flags(name, {})["gluten_source"] is True, name


def test_idli_rava_gluten_free_is_uncertain_not_safe():
    cache.clear()
    r = resolve("idli rava", None)
    ci = to_compliance_input(r, query_atom="idli rava")
    assert ci.verdict_cap == "WARN" or (ci.flags or {}).get("verdict_cap") == "WARN"
    assert "usually_parboiled_rice_check_blend" in (ci.flags.get("uncertainty_flags") or [])
    v = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"gluten_free": "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )
    assert v != "SAFE"
    assert v != "NOT_SAFE"
