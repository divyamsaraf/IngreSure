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


def to_compliance_input(
    resolved, *, trace: bool = False, may_contain: bool = False
) -> ComplianceInput:
    group = resolved.group
    trusted = bool(getattr(resolved, "trusted", False))

    # Unresolved (L5 / ambiguous): nothing to assert -> fail-closed UNCERTAIN.
    if group is None:
        return ComplianceInput(
            canonical_name="", flags={}, knowledge_state="UNCLASSIFIED",
            trusted=False, alcohol_role=None, verdict_cap=None,
            trace=trace, may_contain=may_contain,
        )

    if isinstance(group, TruthAnchorFact):
        flags = dict(group.flags)
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
    return ComplianceInput(
        canonical_name=getattr(group, "canonical_name", ""),
        flags=flags,
        knowledge_state=getattr(group, "knowledge_state", "UNCLASSIFIED"),
        trusted=trusted,
        alcohol_role=_derive_alcohol_role(getattr(group, "alcohol_role", None), getattr(group, "alcohol_content", None)),
        verdict_cap=getattr(group, "verdict_cap", None),
        trace=trace,
        may_contain=may_contain,
    )
