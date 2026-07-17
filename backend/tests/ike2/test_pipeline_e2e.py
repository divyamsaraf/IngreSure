from core.knowledge.ike2.response import assemble
from core.knowledge.ike2.verdict import to_external
from tests.ike2.golden_runner import load_corpus, run_case_full


def test_pipeline_external_matches_golden():
    mismatches = []
    for case in load_corpus():
        _, _, external, _ = run_case_full(case)
        if external != case["expected_verdict"]:
            mismatches.append(case["raw_input"])
    assert mismatches == [], f"pipeline mismatches: {mismatches}"


def test_b2c_preserves_compliance_verdict():
    case = next(c for c in load_corpus() if c["raw_input"] == "E471")
    _, result, _, profile = run_case_full(case)
    payload = assemble([], result, profile, mode="b2c")
    assert payload["external_verdict"] == to_external(result.verdict)


def test_b2b_strict_on_trace_match():
    case = next(c for c in load_corpus() if "peanut" in c["raw_input"] and "2%" in c["raw_input"])
    _, result, _, profile = run_case_full(case)
    payload = assemble([], result, profile, mode="b2b")
    assert payload["external_verdict"] == "NOT_SAFE"
    assert payload["matched_may_contain"]


def test_compound_terms_never_firm_safe():
    for raw in ("natural flavors", "spices"):
        case = next(c for c in load_corpus() if c["raw_input"] == raw)
        got = run_case_full(case)[2]
        assert got != "SAFE", raw
