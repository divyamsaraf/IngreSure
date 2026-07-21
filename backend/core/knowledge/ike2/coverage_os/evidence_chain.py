from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.verdict import Verdict, to_external


def to_audit_bucket(verdict: Verdict) -> str:
    if verdict == Verdict.SAFE:
        return "Safe"
    if verdict == Verdict.FAIL:
        return "Avoid"
    return "Depends"


@dataclass
class EvidenceChain:
    atom: str
    canonical: Optional[str]
    source: str
    flags: dict
    rule_ids: list[str]
    verdict: str
    internal_verdict: str
    evidence_class: str
    miss_class: Optional[str]
    restriction_id: str
    resolution_layer: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evidence_class(
    flags: dict,
    miss_class: Optional[str],
    verdict: Verdict,
    *,
    verdict_cap: Optional[str] = None,
) -> str:
    if miss_class or verdict in (Verdict.UNCERTAIN, Verdict.WARN):
        if not flags:
            return "insufficient"
    # Compound/umbrella before plant — else spices audit as closed_form_plant.
    cap = verdict_cap or flags.get("verdict_cap")
    if cap == "WARN":
        return "dual_or_compound"
    # Allergen-adjacent BEFORE animalish so fish/shellfish audit as allergen.
    if is_allergen_adjacent(flags):
        return "allergen"
    if is_animalish(flags):
        return "animal"
    if flags.get("plant_origin") and not flags.get("animal_origin"):
        return "closed_form_plant"
    return "insufficient"


def _rule_ids_for_atom(
    compliance_result, *, canonical: Optional[str], atom: str, restriction_id: str
) -> list[str]:
    """Pull real rule identities; filter to this ingredient + this restriction."""
    names = {n for n in (canonical, atom) if n}
    names |= {n.lower() for n in names}
    out: list[str] = []
    for row in getattr(compliance_result, "matched_rules", None) or []:
        if not row.get("triggered"):
            continue
        if row.get("restriction") != restriction_id:
            continue
        c = (row.get("canonical") or "").strip()
        if c not in names and c.lower() not in names:
            continue
        rid = row.get("rule_id")
        if rid and rid not in out:
            out.append(rid)
    return out


def _engine_verdict_for_cell(
    compliance_result, *, canonical: Optional[str], atom: str, restriction_id: str
) -> Verdict:
    """Per-(ingredient, restriction) verdict — never paste-level aggregate."""
    breakdown = getattr(compliance_result, "breakdown", None) or {}
    for name in (canonical, atom):
        if not name:
            continue
        if (name, restriction_id) in breakdown:
            return breakdown[(name, restriction_id)]
        for (c, r), v in breakdown.items():
            if r == restriction_id and str(c).lower() == str(name).lower():
                return v
    worst = None
    names = {n for n in (canonical, atom) if n}
    names |= {n.lower() for n in names}
    for row in getattr(compliance_result, "matched_rules", None) or []:
        if not row.get("triggered"):
            continue
        if row.get("restriction") != restriction_id:
            continue
        c = (row.get("canonical") or "").strip()
        if c not in names and c.lower() not in names:
            continue
        v = row.get("verdict")
        if v is None:
            continue
        worst = v if worst is None else max(worst, v)
    if worst is not None:
        return worst
    return Verdict.UNCERTAIN


def build_chain_from_resolve(
    *,
    atom: str,
    resolved,
    compliance_result,
    restriction_id: str,
    compliance_input=None,
) -> EvidenceChain:
    flags: dict = {}
    canonical = None
    if compliance_input is not None:
        flags = dict(compliance_input.flags or {})
        canonical = compliance_input.canonical_name
    elif getattr(resolved, "group", None) is not None:
        g = resolved.group
        flags = dict(getattr(g, "flags", None) or {})
        canonical = getattr(g, "canonical_name", None)

    engine_verdict = _engine_verdict_for_cell(
        compliance_result,
        canonical=canonical,
        atom=atom,
        restriction_id=restriction_id,
    )
    miss = getattr(resolved, "miss_class", None)
    verdict_cap = None
    if compliance_input is not None:
        verdict_cap = getattr(compliance_input, "verdict_cap", None)

    return EvidenceChain(
        atom=atom,
        canonical=canonical,
        source=getattr(resolved, "source", "unknown") or "unknown",
        flags=flags,
        rule_ids=_rule_ids_for_atom(
            compliance_result,
            canonical=canonical,
            atom=atom,
            restriction_id=restriction_id,
        ),
        verdict=to_audit_bucket(engine_verdict),
        internal_verdict=to_external(engine_verdict),
        evidence_class=_evidence_class(
            flags, miss, engine_verdict, verdict_cap=verdict_cap
        ),
        miss_class=miss,
        restriction_id=restriction_id,
        resolution_layer=getattr(resolved, "resolution_layer", None),
    )
