"""Shadow-mode comparison between the legacy engine and IKE-2.

During shadow runs the legacy verdict is always what the user sees; IKE-2 runs
alongside and every divergence is recorded in `ike2_shadow_diffs`. The gate we
care about most is a *false-safe regression*: legacy said NOT_SAFE but IKE-2
said SAFE. That is the one class of disagreement that could harm a user, so it
gets its own flag and must be zero before cutover.
"""

# External 3-tier verdicts, ordered by severity.
_SEVERITY = {"SAFE": 0, "UNCERTAIN": 1, "NOT_SAFE": 2}


def compare(legacy_verdict: str, ike2_verdict: str, raw_input: str) -> dict:
    match = legacy_verdict == ike2_verdict
    false_safe_regression = (
        _SEVERITY.get(legacy_verdict, 0) > _SEVERITY.get(ike2_verdict, 0)
        and ike2_verdict == "SAFE"
    )
    return {
        "raw_input": raw_input,
        "legacy_verdict": legacy_verdict,
        "ike2_verdict": ike2_verdict,
        "match": match,
        "false_safe_regression": false_safe_regression,
    }
