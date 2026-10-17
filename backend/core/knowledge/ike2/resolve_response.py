"""IKE-2 resolve result → fact-only HTTP response fields (Item 33 Prompt 2).

Pure mapping. Does not resolve, enqueue, or write groups. Flag flattening goes
through ``seam.to_compliance_input`` so this surface cannot drift from compliance.
"""
from __future__ import annotations

from typing import Any, Optional

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS
from core.knowledge.ike2.seam import to_compliance_input

_STATIC_LAYERS = frozenset({"L1_truth_anchor", "L2_local_ontology"})


def _source_layer(resolved) -> str:
    if getattr(resolved, "status", None) != "resolved" or getattr(resolved, "group", None) is None:
        return "unknown"
    layer = getattr(resolved, "resolution_layer", "") or ""
    if layer in _STATIC_LAYERS:
        return "static"
    if layer.startswith("L3_db"):
        return "dynamic"
    return "unknown"


def _confidence_band(resolved) -> Optional[str]:
    if _source_layer(resolved) == "unknown":
        return None
    raw = getattr(resolved, "confidence_band", None)
    if raw in ("exact", "high"):
        return "high"
    if raw in ("medium", "low"):
        return raw
    return None


def _nut_source(flags: dict, *, peanut: bool, tree_nut: bool) -> Optional[str]:
    bits = []
    if peanut:
        bits.append("peanut")
    if tree_nut:
        bits.append("tree_nut")
    if bits:
        return ",".join(bits)
    raw = flags.get("nut_source")
    return raw if raw else None


def _ingredient_dict(resolved, flattened) -> dict[str, Any]:
    flags = flattened.flags
    group = resolved.group
    group_id = getattr(group, "id", None)
    out: dict[str, Any] = {
        "id": str(group_id) if group_id else flattened.canonical_name,
        "canonical_name": flattened.canonical_name,
        "aliases": list(flags.get("aliases") or []),
        "uncertainty_flags": list(flags.get("uncertainty_flags") or []),
        "animal_species": flags.get("animal_species"),
        "alcohol_content": flags.get("alcohol_content"),
        "alcohol_role": flattened.alcohol_role,
        "verdict_cap": flattened.verdict_cap,
        "regions": list(flags.get("regions") or []),
    }
    for flag in BOOL_FLAGS:
        out[flag] = bool(flags.get(flag))
    out["nut_source"] = _nut_source(
        flags, peanut=out["peanut_source"], tree_nut=out["tree_nut_source"]
    )
    return out


def map_ike2_to_resolved_response(resolved) -> dict[str, Any]:
    """Map one IKE-2 ``ResolvedIngredient`` onto ``ResolvedIngredientResponse`` fields.

    Uncertain / missing group → ``ingredient=None`` and ``knowledge_state=UNCLASSIFIED``.
    Never returns ``source_layer="api"`` (enrichment is offline).
    """
    source_layer = _source_layer(resolved)
    if source_layer == "unknown":
        return {
            "ingredient": None,
            "source_layer": "unknown",
            "confidence_band": None,
            "knowledge_state": "UNCLASSIFIED",
            "knowledge_source": getattr(resolved, "source", None) or "unknown_queue",
        }

    flattened = to_compliance_input(resolved)
    return {
        "ingredient": _ingredient_dict(resolved, flattened),
        "source_layer": source_layer,
        "confidence_band": _confidence_band(resolved),
        "knowledge_state": flattened.knowledge_state,
        "knowledge_source": getattr(resolved, "source", None) or "",
    }
