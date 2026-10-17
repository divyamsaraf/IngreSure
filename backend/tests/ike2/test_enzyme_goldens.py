"""Item 3.1 Prompt 4: enzyme subtype goldens + Jain yeast/tempeh never-SAFE."""
from types import SimpleNamespace

from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict, to_external


def _ci(**flags):
    ks = flags.pop("knowledge_state", "VERIFIED")
    trusted = flags.pop("trusted", True)
    verdict_cap = flags.pop("verdict_cap", None)
    return SimpleNamespace(
        canonical_name=flags.pop("canonical_name", "x"),
        flags=flags,
        knowledge_state=ks,
        trusted=trusted,
        verdict_cap=verdict_cap,
        alcohol_role=flags.get("alcohol_role", "none"),
        trace=False,
        may_contain=False,
    )


def _eval(flags: dict, restriction_ids: list[str]):
    profile = SimpleNamespace(
        restrictions={rid: "medical" for rid in restriction_ids}
    )
    return evaluate([_ci(**flags)], profile, rules_module.seeded_rules())


def test_animal_rennet_avoid_under_vegan_vegetarian_jain():
    flags = {
        "canonical_name": "rennet",
        "animal_origin": True,
        "enzyme_animal_source": True,
    }
    for rid in ("vegan", "vegetarian", "jain", "lacto_vegetarian", "hindu_vegetarian"):
        result = _eval(flags, [rid])
        assert result.verdict == Verdict.FAIL, rid


def test_pepsin_avoid_under_vegan():
    result = _eval(
        {"canonical_name": "pepsin", "animal_origin": True, "enzyme_animal_source": True},
        ["vegan"],
    )
    assert result.verdict == Verdict.FAIL


def test_microbial_enzyme_not_animal_fail_under_vegan():
    """Microbial enzyme without animal flags must not trip enzyme_animal_source rules."""
    result = _eval(
        {
            "canonical_name": "microbial rennet",
            "animal_origin": False,
            "enzyme_microbial_source": True,
            "enzyme_animal_source": False,
        },
        ["vegan"],
    )
    assert result.verdict == Verdict.SAFE


def test_bare_enzymes_unknown_never_firm_safe_under_vegan():
    result = _eval(
        {
            "canonical_name": "enzymes",
            "verdict_cap": "WARN",
            "animal_origin": False,
        },
        ["vegan"],
    )
    assert result.verdict != Verdict.SAFE
    assert to_external(result.verdict) != "SAFE"


def test_jain_yeast_tempeh_never_firm_safe_still_holds():
    """Regression: Item 16 fungal class remains green after enzyme work."""
    from core.bridge import _run_ike2_compliance, map_ike2_to_compliance_verdict

    for label in ("yeast", "yeast extract", "tempeh", "baker's yeast"):
        result, inputs, display = _run_ike2_compliance([label], ["jain"])
        verdict = map_ike2_to_compliance_verdict(
            result, inputs, input_display_map=display
        )
        assert verdict.status.value != "SAFE", label
