from core.knowledge.ike2.verdict import Verdict, aggregate, to_external


def test_aggregate_most_severe_wins():
    assert aggregate([Verdict.SAFE, Verdict.WARN, Verdict.SAFE]) == Verdict.WARN
    assert aggregate([Verdict.SAFE, Verdict.FAIL, Verdict.WARN]) == Verdict.FAIL
    assert aggregate([Verdict.SAFE, Verdict.SAFE]) == Verdict.SAFE
    assert aggregate([]) == Verdict.UNCERTAIN


def test_warn_maps_to_depends_never_safe():
    assert to_external(Verdict.WARN) == "UNCERTAIN"
    assert to_external(Verdict.UNCERTAIN) == "UNCERTAIN"
    assert to_external(Verdict.FAIL) == "NOT_SAFE"
    assert to_external(Verdict.SAFE) == "SAFE"
