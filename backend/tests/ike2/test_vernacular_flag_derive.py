"""Indian vernacular tokens in flag_derive → L5 label-derived Avoid."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external


def test_dahi_derives_dairy():
    assert derive_identity_flags("dahi", {})["dairy_source"] is True


def test_anda_derives_egg():
    assert derive_identity_flags("anda", {})["egg_source"] is True


def test_idli_rava_not_gluten():
    flags = derive_identity_flags("idli rava", {})
    assert flags.get("gluten_source") is not True


def test_rava_alone_still_gluten():
    assert derive_identity_flags("rava", {})["gluten_source"] is True


def test_vernacular_tree_nut_and_sesame_mustard():
    assert derive_identity_flags("kaju", {})["tree_nut_source"] is True
    assert derive_identity_flags("badam", {})["tree_nut_source"] is True
    assert derive_identity_flags("til", {})["sesame_source"] is True
    assert derive_identity_flags("rai", {})["mustard_source"] is True
    assert derive_identity_flags("sarson", {})["mustard_source"] is True
    assert derive_identity_flags("sarson oil", {}).get("mustard_source") is not True


def _verdict(name: str, rid: str) -> str:
    cache.clear()
    r = resolve(name, None)
    ci = to_compliance_input(r, query_atom=name)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )


def test_l5_dahi_not_safe_under_dairy_free():
    assert _verdict("dahi", "dairy_free") == "NOT_SAFE"


def test_l5_anda_not_safe_under_egg_free():
    assert _verdict("anda", "egg_free") == "NOT_SAFE"
