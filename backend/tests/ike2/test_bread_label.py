from tests.ike2.golden_runner import run_case_full
from tests.test_label_decomposer import BREAD_LABEL


def test_bread_label_gluten_free_not_safe():
    case = {
        "raw_input": BREAD_LABEL,
        "profile": {"restrictions": {"gluten_free": "medical"}},
        "region": None,
    }
    _, _, external, _ = run_case_full(case)
    assert external == "NOT_SAFE"


def test_bread_label_vegan_staples_resolve_trusted():
    """Staples + L3 aliases resolve trusted (enzymes/riboflavin may still WARN for vegan)."""
    from core.knowledge.ike2.input_layer import parse_atoms
    from core.knowledge.ike2.resolver import resolve
    from tests.test_label_decomposer import BREAD_LABEL

    atoms = parse_atoms(BREAD_LABEL)
    names = {a.name for a in atoms}
    assert "water" in names
    assert "yeast" in names
    for staple in ("water", "yeast", "salt"):
        resolved = resolve(staple, None)
        assert resolved.trusted, staple
