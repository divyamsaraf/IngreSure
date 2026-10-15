"""Item 2.1 — process-flag OR propagation for compound decomposition.

Process identity (``fungal``, ``fermented``) must survive expansion into
compositional members. Compositional allergen/origin flags are **not** copied
from parent → member by this helper.
"""
from __future__ import annotations

from typing import Any, Mapping

# Agreed set (Item 2 Prompt 1 decision). Expand only via explicit later decision.
PROCESS_FLAG_SET: frozenset[str] = frozenset({"fungal", "fermented"})


def propagate_process_flags(
    parent_flags: Mapping[str, Any],
    member_flags: Mapping[str, Any],
) -> dict[str, Any]:
    """Return member flags with parent process flags OR'd in (never clear positives).

    - Only keys in ``PROCESS_FLAG_SET`` are propagated from parent.
    - Member positives outside that set are preserved unchanged.
    - Does not invent compositional allergens (e.g. ``dairy_source``) from parent.
    """
    out = dict(member_flags)
    for flag in PROCESS_FLAG_SET:
        if parent_flags.get(flag):
            out[flag] = True
    return out
