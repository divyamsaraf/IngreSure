from tests.ike2.golden_runner import load_corpus, run_case


def test_zero_false_safe_regressions():
    false_safes = []
    for case in load_corpus():
        got = run_case(case)
        must_not = case.get("must_not_be_safe", case["expected_verdict"] != "SAFE")
        if must_not and got == "SAFE":
            false_safes.append(case["raw_input"])
    assert false_safes == [], f"FALSE-SAFE regressions: {false_safes}"
