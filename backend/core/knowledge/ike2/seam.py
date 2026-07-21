"""Resolver -> compliance seam.

``resolver.resolve`` returns a :class:`ResolvedIngredient` whose payload lives on
``.group`` (a :class:`TruthAnchorFact` with a ``.flags`` dict, or a flat db
``GroupRow``, or ``None``). ``compliance.evaluate`` instead reads a *flattened*
ingredient: ``canonical_name``, ``flags`` (dict), ``knowledge_state``,
``trusted``, ``verdict_cap``, ``alcohol_role``, ``trace``.

This module is the single, lossless, fail-closed bridge between the two shapes —
the point at which a bulk-mapped flag (peanut_source, alcohol_role, ...) starts
actually driving a verdict.
"""
from dataclasses import dataclass
from typing import Optional

from core.knowledge.ike2.truth_anchor import TruthAnchorFact
from core.knowledge.ike2.flag_derive import derive_identity_flags


@dataclass
class ComplianceInput:
    """The flattened shape ``compliance.evaluate`` consumes."""
    canonical_name: str
    flags: dict
    knowledge_state: str
    trusted: bool
    alcohol_role: Optional[str]
    verdict_cap: Optional[str]
    trace: bool
    may_contain: bool = False


def _derive_alcohol_role(explicit, alcohol_content) -> Optional[str]:
    """Compliance keys the alcohol rule off ``alcohol_role``. Some sources only
    carry ``alcohol_content`` (e.g. the ethanol truth anchor); deriving the role
    here prevents an alcohol false-SAFE. Fail-closed: any alcohol => ingredient."""
    if explicit is not None:
        return explicit
    if alcohol_content is not None and alcohol_content > 0:
        return "ingredient"
    return None


def _with_derived_flags(canonical_name: str, flags: dict) -> dict:
    """OR identity-derived allergen bits onto flags (fish from species, peanut from name, ...)."""
    derived = derive_identity_flags(
        canonical_name,
        flags,
        animal_species=flags.get("animal_species"),
    )
    out = dict(flags)
    for key, value in derived.items():
        if value is True:
            out[key] = True
        elif key == "animal_species" and value and not out.get("animal_species"):
            out[key] = value
    return out


def to_compliance_input(
    resolved,
    *,
    trace: bool = False,
    may_contain: bool = False,
    query_atom: Optional[str] = None,
) -> ComplianceInput:
    group = resolved.group
    trusted = bool(getattr(resolved, "trusted", False))

    # Unresolved (L5 / ambiguous): nothing to assert -> fail-closed UNCERTAIN.
    # Keep the original atom text as identity so multiple unknowns do not collapse
    # onto one empty breakdown key (and so the audit never shows a bare "Unknown").
    if group is None:
        identity = (query_atom or "").strip()
        return ComplianceInput(
            canonical_name=identity, flags={}, knowledge_state="UNCLASSIFIED",
            trusted=False, alcohol_role=None, verdict_cap=None,
            trace=trace, may_contain=may_contain,
        )

    if isinstance(group, TruthAnchorFact):
        flags = _with_derived_flags(group.canonical_name, dict(group.flags))
        return ComplianceInput(
            canonical_name=group.canonical_name,
            flags=flags,
            knowledge_state=group.knowledge_state,
            trusted=trusted,
            alcohol_role=_derive_alcohol_role(flags.get("alcohol_role"), flags.get("alcohol_content")),
            verdict_cap=flags.get("verdict_cap"),
            trace=trace,
            may_contain=may_contain,
        )

    # db GroupRow: every column is a flat attribute, so its __dict__ already is the
    # flags map compliance looks flags.get(trigger_flag) into.
    flags = dict(vars(group))
    canon = getattr(group, "canonical_name", "") or ""
    flags = _with_derived_flags(canon, flags)
    return ComplianceInput(
        canonical_name=canon,
        flags=flags,
        knowledge_state=getattr(group, "knowledge_state", "UNCLASSIFIED"),
        trusted=trusted,
        alcohol_role=_derive_alcohol_role(getattr(group, "alcohol_role", None), getattr(group, "alcohol_content", None)),
        verdict_cap=getattr(group, "verdict_cap", None) or flags.get("verdict_cap"),
        trace=trace,
        may_contain=may_contain,
    )
