"""Golden: pantry false friends must not Avoid under the implied restriction."""
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external

_CASES = (
    ("peanut butter", "dairy_free"),
    ("organic peanut butter smooth", "dairy_free"),
    ("cocoa butter", "dairy_free"),
    ("cream of tartar", "dairy_free"),
    ("coconut cream", "dairy_free"),
    ("eggplant", "egg_free"),
    ("buckwheat", "gluten_free"),
    ("idli rava", "gluten_free"),
    ("nutmeg", "tree_nut_allergy"),
    ("water chestnut", "tree_nut_allergy"),
    ("lobster mushroom", "shellfish_allergy"),
    ("almond milk", "dairy_free"),
)


def test_false_friends_never_not_safe():
    for name, rid in _CASES:
        cache.clear()
        r = resolve(name, None)
        ci = to_compliance_input(r, query_atom=name)
        v = to_external(
            evaluate(
                [ci],
                SimpleNamespace(restrictions={rid: "medical"}),
                rules_module.seeded_rules(),
            ).verdict
        )
        assert v != "NOT_SAFE", f"{name!r} under {rid} → {v}"
