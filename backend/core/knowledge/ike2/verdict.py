from enum import IntEnum


class Verdict(IntEnum):
    SAFE = 0
    UNCERTAIN = 1
    WARN = 2
    FAIL = 3


def aggregate(verdicts):
    if not verdicts:
        return Verdict.UNCERTAIN
    return max(verdicts)


_EXTERNAL = {
    Verdict.FAIL: "NOT_SAFE",
    Verdict.WARN: "UNCERTAIN",
    Verdict.UNCERTAIN: "UNCERTAIN",
    Verdict.SAFE: "SAFE",
}


def to_external(v):
    return _EXTERNAL[v]
