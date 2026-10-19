"""Comparison between the legacy engine and IKE-2 (primary).

IKE-2 is the primary pipeline; legacy now runs only for comparison, and every
divergence is recorded in `ike2_shadow_diffs`.

``false_safe_regression`` is **not** "IKE-2 SAFE while legacy was worse."
Legacy UNCERTAIN often means "legacy could not resolve," not ground truth.
A regression is flagged only when IKE-2 returned SAFE but at least one active
restriction has a FAIL/WARN rule whose trigger matches an ingredient's flags —
i.e. IKE-2's own rule engine implies Avoid/Depends should have fired.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

# External 3-tier verdicts (match still compares these strings).
_SEVERITY = {"SAFE": 0, "UNCERTAIN": 1, "NOT_SAFE": 2}


def _flag_triggered(flags: Mapping[str, Any], trigger_flag: str) -> bool:
    if not trigger_flag:
        return False
    if trigger_flag in flags and flags.get(trigger_flag) is None:
        return False  # explicit null = never evaluated; not a definite hit
    return bool(flags.get(trigger_flag))


def _composite_triggered(flags: Mapping[str, Any], field: str) -> bool:
    """Minimal composites used by RULE_SEED (keep in sync with compliance kinds)."""
    if field == "meat_fish_derived":
        if flags.get("dairy_source") or flags.get("egg_source") or flags.get("insect_derived") or flags.get("bee_product"):
            return False
        return bool(flags.get("animal_origin") or flags.get("fish_source") or flags.get("shellfish_source"))
    if field == "meat_land_derived":
        if (
            flags.get("dairy_source")
            or flags.get("egg_source")
            or flags.get("insect_derived")
            or flags.get("bee_product")
            or flags.get("fish_source")
            or flags.get("shellfish_source")
        ):
            return False
        return bool(flags.get("animal_origin"))
    if field == "alcohol_role":
        role = flags.get("alcohol_role")
        return role not in (None, "none", "")
    if field == "alcohol_content":
        try:
            return flags.get("alcohol_content") is not None and float(flags.get("alcohol_content")) > 0
        except (TypeError, ValueError):
            return False
    return False


def _rule_matches_flags(rule, flags: Mapping[str, Any]) -> bool:
    """True when a seeded/DB rule would trigger on this ingredient's flags."""
    kind = getattr(rule, "kind", "flag")
    action = getattr(rule, "action", "FAIL")
    if action not in ("FAIL", "WARN"):
        return False

    if kind == "flag":
        return _flag_triggered(flags, getattr(rule, "trigger_flag", None) or "")
    if kind in ("meat_fish_derived", "meat_land_derived"):
        return _composite_triggered(flags, kind)
    if kind == "alcohol":
        return _composite_triggered(flags, "alcohol_role")
    if kind == "alcohol_content":
        return _composite_triggered(flags, "alcohol_content")
    if kind == "species_match":
        species = flags.get("animal_species")
        target = getattr(rule, "match_value", None)
        return species is not None and species == target
    if kind == "species_in_list":
        species = flags.get("animal_species")
        allowed = getattr(rule, "match_value", None)
        if not isinstance(allowed, (list, tuple)):
            allowed = [allowed]
        return species in allowed
    # Unknown kind: do not invent a regression.
    return False


def _ike2_should_have_blocked(
    restriction_ids: Optional[Sequence[str]],
    ingredient_flags: Optional[Sequence[Mapping[str, Any]]],
    *,
    rules: Optional[Iterable[Any]] = None,
) -> bool:
    """True if any active FAIL/WARN rule matches any ingredient's flags."""
    if not restriction_ids or not ingredient_flags:
        return False
    active = set(restriction_ids)
    if rules is None:
        from core.knowledge.ike2 import rules as rules_module

        rules = rules_module.load_rules()
    for rule in rules:
        if getattr(rule, "restriction", None) not in active:
            continue
        for flags in ingredient_flags:
            if flags and _rule_matches_flags(rule, flags):
                return True
    return False


def compare(
    legacy_verdict: str,
    ike2_verdict: str,
    raw_input: str,
    *,
    restriction_ids: Optional[Sequence[str]] = None,
    ingredient_flags: Optional[Sequence[Mapping[str, Any]]] = None,
    rules: Optional[Iterable[Any]] = None,
) -> dict:
    """Diff a legacy verdict against the primary (IKE-2) verdict.

    ``match`` is still legacy vs IKE-2 string equality (observational).

    ``false_safe_regression`` is True only when IKE-2 said SAFE **and** at least
    one active ``restriction_ids`` entry has a FAIL/WARN rule whose trigger
    matches an ingredient's flags. Legacy severity alone never sets this flag.
    """
    match = legacy_verdict == ike2_verdict
    false_safe_regression = False
    if ike2_verdict == "SAFE":
        false_safe_regression = _ike2_should_have_blocked(
            restriction_ids, ingredient_flags, rules=rules
        )
    return {
        "raw_input": raw_input,
        "legacy_verdict": legacy_verdict,
        "ike2_verdict": ike2_verdict,
        "match": match,
        "false_safe_regression": false_safe_regression,
        "restriction_ids": list(restriction_ids) if restriction_ids else [],
    }
