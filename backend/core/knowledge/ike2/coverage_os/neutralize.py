"""Typed neutralize policies for compound phrases (Coverage OS Phase 2a).

Policy types are a closed enum. Ontology rows carry ``role`` matching those
values. Plant-mod partner detection uses ``deny_lists.is_animalish`` on
existing origin flags — not a new dairy/meat keyword list.

``policy_fired`` may include audit tag ``tier1_keep`` (not a role enum value).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Mapping

from core.knowledge.ike2.coverage_os.deny_lists import is_animalish

PolicyType = Literal["plant_mod", "dairy_head", "process_keep", "culinary_keep"]

_VALID_ROLES = frozenset({"plant_mod", "dairy_head", "process_keep", "culinary_keep"})

# Patchable alias for Tier-1 fallback (LCT-2).
try:
    from core.knowledge.ike2 import truth_anchor as _truth_anchor

    truth_anchor_lookup = _truth_anchor.lookup
except Exception:  # pragma: no cover
    def truth_anchor_lookup(name: str):  # type: ignore[misc]
        return None


@dataclass
class PolicyResult:
    atoms: list[str]
    policy_fired: list[str] = field(default_factory=list)
    derived_from: dict[str, str] = field(default_factory=dict)
    verdict_cap: str | None = None


def build_role_index(ingredients: list[dict]) -> dict[str, str]:
    """Map normalized canonical (+ aliases) → role string."""
    index: dict[str, str] = {}
    for row in ingredients or []:
        role = str(row.get("role") or "").strip()
        if role not in _VALID_ROLES:
            continue
        name = str(row.get("canonical_name") or "").strip().lower()
        if name:
            index[name] = role
        for alias in row.get("aliases") or []:
            key = str(alias or "").strip().lower()
            if key:
                index[key] = role
    return index


def _default_lookup_flags(token: str) -> Mapping | None:
    key = (token or "").strip().lower()
    if not key:
        return None
    try:
        from core.knowledge.ike2 import truth_anchor
        fact = truth_anchor.lookup(key)
        if fact is not None and getattr(fact, "flags", None) is not None:
            return dict(fact.flags)
    except Exception:
        pass
    try:
        from core.knowledge.ike2.stores import local_ontology
        fact = local_ontology.lookup(key)
        if fact is not None and getattr(fact, "flags", None) is not None:
            return dict(fact.flags)
    except Exception:
        pass
    return None


def _is_animalish_partner(
    token: str,
    *,
    role_index: Mapping[str, str],
    lookup_flags: Callable[[str], Mapping | None],
) -> bool:
    if role_index.get(token) == "dairy_head":
        return True
    flags = lookup_flags(token)
    return is_animalish(dict(flags) if flags else None)


def _process_keep_bases(
    tokens: list[str],
    *,
    role_index: Mapping[str, str],
    lookup_flags: Callable[[str], Mapping | None],
) -> list[str]:
    """Function-local process_keep extract: animalish tokens via is_animalish only."""
    bases: list[str] = []
    for tok in tokens:
        if role_index.get(tok) in ("process_keep", "culinary_keep", "plant_mod"):
            continue
        if _is_animalish_partner(tok, role_index=role_index, lookup_flags=lookup_flags):
            bases.append(tok)
    return bases


def apply_policies(
    phrase: str,
    *,
    role_index: Mapping[str, str],
    lookup_flags: Callable[[str], Mapping | None] | None = None,
) -> PolicyResult:
    """Apply typed neutralize policies to a multi-word (or single) phrase.

    LCT-2 keep order:
      1. culinary_keep / process_keep
      2. plant_mod / dairy_head (LCT-1: plant_mod before dairy_head)
      3. truth_anchor_lookup(full_phrase) → tier1_keep
      4. passthrough [phrase]  (no generic keyword tear)
    """
    raw = (phrase or "").strip()
    if not raw:
        return PolicyResult(atoms=[])

    flags_fn = lookup_flags if lookup_flags is not None else _default_lookup_flags
    tokens = raw.lower().split()
    if len(tokens) <= 1:
        return PolicyResult(atoms=[raw], policy_fired=[], derived_from={})

    # --- LCT-2 step 1: culinary_keep / process_keep ---
    has_culinary = any(role_index.get(t) == "culinary_keep" for t in tokens)
    has_process = any(role_index.get(t) == "process_keep" for t in tokens)
    if has_culinary:
        return PolicyResult(
            atoms=[raw],
            policy_fired=["culinary_keep"],
            derived_from={},
        )
    if has_process:
        bases = _process_keep_bases(
            tokens, role_index=role_index, lookup_flags=flags_fn,
        )
        derived = {b: raw for b in bases}
        atoms = [raw] + bases
        return PolicyResult(
            atoms=atoms,
            policy_fired=["process_keep"],
            derived_from=derived,
        )

    # --- LCT-2 step 2 / LCT-1: plant_mod BEFORE dairy_head ---
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if role_index.get(a) == "plant_mod" and _is_animalish_partner(
            b, role_index=role_index, lookup_flags=flags_fn,
        ):
            plant = a
            return PolicyResult(
                atoms=[raw, plant],
                policy_fired=["plant_mod"],
                derived_from={plant: raw},
            )
        if role_index.get(b) == "plant_mod" and _is_animalish_partner(
            a, role_index=role_index, lookup_flags=flags_fn,
        ):
            plant = b
            return PolicyResult(
                atoms=[raw, plant],
                policy_fired=["plant_mod"],
                derived_from={plant: raw},
            )

    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if role_index.get(a) == "dairy_head" or role_index.get(b) == "dairy_head":
            return PolicyResult(
                atoms=[raw],
                policy_fired=["dairy_head"],
                derived_from={},
            )

    # --- LCT-2 step 3: Tier-1 truth_anchor keep ---
    if truth_anchor_lookup(raw) is not None:
        return PolicyResult(
            atoms=[raw],
            policy_fired=["tier1_keep"],
            derived_from={},
        )

    # --- LCT-2 step 4: passthrough (no generic tear) ---
    return PolicyResult(atoms=[raw], policy_fired=[], derived_from={})
