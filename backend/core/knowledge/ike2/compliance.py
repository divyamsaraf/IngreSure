from typing import Optional

from core.knowledge.ike2 import truth_anchor
from core.knowledge.ike2.verdict import Verdict, aggregate

# Knowledge-state ranking for the C2 min_knowledge_state gate.
_KS_RANK = {
    "UNCLASSIFIED": 0,
    "DISCOVERED": 1,
    "AUTO_CLASSIFIED": 2,
    "CLASSIFIED": 3,
    "VERIFIED": 4,
    "LOCKED": 5,
}


class ComplianceResult:
    """Holds the aggregate verdict plus the per-match breakdown.

    Compares equal to a bare ``Verdict`` (so callers can assert on the headline
    verdict directly) while still exposing ``.verdict`` and the detail lists.
    """

    def __init__(
        self,
        verdict: Verdict,
        matched_contains,
        matched_may_contain,
        caution_reasons,
        breakdown,
    ):
        self.verdict = verdict
        self.matched_contains = matched_contains
        self.matched_may_contain = matched_may_contain
        self.caution_reasons = caution_reasons
        self.breakdown = breakdown

    def __eq__(self, other):
        if isinstance(other, Verdict):
            return self.verdict == other
        if isinstance(other, ComplianceResult):
            return self.verdict == other.verdict
        return NotImplemented

    def __hash__(self):
        return hash(self.verdict)

    def __repr__(self):
        return f"ComplianceResult({self.verdict!r})"


def _effective_flags(r) -> dict:
    """C1: re-check the truth anchor; locked facts override resolved flags."""
    flags = dict(getattr(r, "flags", {}) or {})
    fact = truth_anchor.lookup(getattr(r, "canonical_name", "") or "")
    if fact is not None:
        flags.update(fact.flags)
    return flags


def _ks_gate_ok(knowledge_state: str, rule) -> bool:
    """C2: rule may only assert a definite verdict at/above its min state."""
    minimum = getattr(rule, "min_knowledge_state", "UNCLASSIFIED")
    return _KS_RANK.get(knowledge_state, 0) >= _KS_RANK.get(minimum, 0)


def _verdict_for(r, rule, severity: Optional[str]):
    """C3: one ingredient × one rule -> (verdict, triggered, trace)."""
    flags = _effective_flags(r)
    severity = severity or "medical"  # unknown severity is treated conservatively
    trusted = bool(getattr(r, "trusted", False))
    knowledge_state = getattr(r, "knowledge_state", "UNCLASSIFIED")
    cap = getattr(r, "verdict_cap", None)
    trace = bool(getattr(r, "trace", False))

    if getattr(rule, "kind", "flag") == "alcohol":
        role = getattr(r, "alcohol_role", None)
        triggered = role is not None
    else:
        role = None
        triggered = bool(flags.get(rule.trigger_flag))

    # Untrusted resolutions may never drive Avoid or Safe -> always UNCERTAIN.
    if not trusted:
        return Verdict.UNCERTAIN, triggered, trace

    # Base verdict from the trigger.
    if not triggered:
        base = Verdict.SAFE
    elif role is not None:  # alcohol
        base = Verdict.FAIL if role == "ingredient" else Verdict.WARN
    elif trace:  # may_contain match
        base = Verdict.FAIL if severity == "medical" else Verdict.WARN
    else:  # definite contains
        base = Verdict.FAIL

    # Compound/ambiguous terms can never be definitive -> WARN.
    if cap == "WARN":
        return Verdict.WARN, triggered, trace

    # A definite FAIL needs sufficient knowledge state to stand.
    if base == Verdict.FAIL and not _ks_gate_ok(knowledge_state, rule):
        return Verdict.UNCERTAIN, triggered, trace

    # Conservative knowledge-state propagation on a clean pass.
    if base == Verdict.SAFE:
        if knowledge_state == "UNCLASSIFIED":
            return Verdict.UNCERTAIN, triggered, trace
        if knowledge_state == "DISCOVERED":
            return Verdict.WARN, triggered, trace

    return base, triggered, trace


def evaluate(resolved, profile, rules) -> ComplianceResult:
    """C4: aggregate the most-severe verdict across all ingredients × rules."""
    restrictions = getattr(profile, "restrictions", {}) or {}
    verdicts = []
    matched_contains = []
    matched_may_contain = []
    caution_reasons = []
    breakdown = {}

    for r in resolved:
        for rule in rules:
            if rule.restriction not in restrictions:
                continue
            severity = restrictions.get(rule.restriction)
            verdict, triggered, trace = _verdict_for(r, rule, severity)
            verdicts.append(verdict)
            name = getattr(r, "canonical_name", "?")
            breakdown[(name, rule.restriction)] = verdict
            if triggered:
                (matched_may_contain if trace else matched_contains).append(name)
            if verdict != Verdict.SAFE:
                caution_reasons.append(f"{rule.restriction}:{name}")

    return ComplianceResult(
        aggregate(verdicts),
        matched_contains,
        matched_may_contain,
        caution_reasons,
        breakdown,
    )
