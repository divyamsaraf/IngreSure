from tests.ike2.golden_runner import load_corpus, run_case


def test_golden_exact_verdicts():
    mismatches = []
    for case in load_corpus():
        got = run_case(case)
        exp = case["expected_verdict"]
        if got != exp:
            mismatches.append(f"{case['raw_input']!r}: expected {exp}, got {got}")
    assert mismatches == [], "Golden verdict mismatches:\n" + "\n".join(mismatches)
