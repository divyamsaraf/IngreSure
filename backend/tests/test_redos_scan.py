"""ReDoS scan: parsing + flag_derive regexes must stay under the per-payload budget."""
from scripts.redos_scan import BUDGET_S, load_patterns, scan, timed_search


def test_loads_parsing_and_derive_regexes():
    patterns = load_patterns()
    origins = " ".join(origin for origin, _ in patterns)
    assert "core.parsing" in origins or "ingredient_parser" in origins
    assert patterns, "expected compiled regexes from parsing / derive modules"


def test_redos_scan_passes_product_regexes():
    slow = scan()
    assert slow == [], slow


def test_catastrophic_regex_exceeds_budget():
    import re

    evil = re.compile(r"(a+)+$")
    elapsed, exceeded = timed_search(evil, "a" * 28 + "b", budget=BUDGET_S)
    assert exceeded or elapsed >= BUDGET_S
