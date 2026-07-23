from __future__ import annotations

from dataclasses import dataclass

from core.knowledge.ike2.coverage_os.induction.types import A1_DANGEROUS
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


@dataclass(frozen=True)
class DecisionRecord:
    candidate_key: str
    accepted: bool
    safety_class: str
    demoted_for_safety: bool = False


@dataclass(frozen=True)
class PrecisionReport:
    n_decisions: int
    accept_rate: float
    a1_n: int
    a1_accept_rate: float
    a2_demote_for_safety_count: int
    meets_a: bool
    meets_a1: bool
    meets_a2: bool


def demote_reason_is_safety(reason: str | None) -> bool:
    """A2: demote reason contains substring 'safety' (case-insensitive)."""
    return "safety" in str(reason or "").lower()


def iter_induced_decisions(
    ledger: PromoteLedger,
    *,
    source: str = "phase2b_induction",
) -> list[DecisionRecord]:
    rows = list(ledger.iter_rows())
    ordered_keys: list[str] = []
    accepted: dict[str, bool] = {}
    safety: dict[str, str] = {}
    demoted_safety: dict[str, bool] = {}

    for row in rows:
        if row.get("source") != source and row.get("kind") != "demoted":
            continue
        key = str(row.get("candidate_key") or "")
        if not key:
            continue
        kind = row.get("kind")
        if kind == "promoted" and row.get("source") == source and row.get("auto") is False:
            if key in accepted:
                continue
            ind = (row.get("payload") or {}).get("induction") or {}
            sc = ind.get("safety_class")
            if not sc:
                continue
            ordered_keys.append(key)
            accepted[key] = True
            safety[key] = str(sc)
            demoted_safety[key] = False
        elif (
            kind == "confirmed_non_promotable"
            and row.get("source") == source
            and str(row.get("reason") or "") == "reviewer_reject"
        ):
            if key in accepted:
                continue
            ind = (row.get("payload") or {}).get("induction") or {}
            sc = ind.get("safety_class") or "role_only"
            ordered_keys.append(key)
            accepted[key] = False
            safety[key] = str(sc)
            demoted_safety[key] = False
        elif kind == "demoted" and key in accepted and accepted[key]:
            if demote_reason_is_safety(row.get("reason")):
                demoted_safety[key] = True

    return [
        DecisionRecord(
            candidate_key=k,
            accepted=accepted[k],
            safety_class=safety[k],
            demoted_for_safety=demoted_safety[k],
        )
        for k in ordered_keys
    ]


def measure_precision(
    records: list[DecisionRecord],
    *,
    window: int = 50,
) -> PrecisionReport:
    windowed = records[:window]
    n = len(windowed)
    accepts = sum(1 for r in windowed if r.accepted)
    accept_rate = (accepts / n) if n else 0.0
    a1 = [r for r in windowed if r.safety_class in A1_DANGEROUS]
    a1_n = len(a1)
    a1_accepts = sum(1 for r in a1 if r.accepted)
    a1_rate = (a1_accepts / a1_n) if a1_n else 0.0
    a2_count = sum(1 for r in windowed if r.demoted_for_safety)
    meets_a = n >= window and accept_rate >= 0.70
    meets_a1 = a1_n >= 10 and a1_rate >= 0.90
    meets_a2 = a2_count == 0
    return PrecisionReport(
        n_decisions=n,
        accept_rate=accept_rate,
        a1_n=a1_n,
        a1_accept_rate=a1_rate,
        a2_demote_for_safety_count=a2_count,
        meets_a=meets_a,
        meets_a1=meets_a1,
        meets_a2=meets_a2,
    )
