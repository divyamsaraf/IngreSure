"""IKE-2 helpers retained after legacy engine removal (Item 16 Prompt 7).

``ike2_external_verdict``, flag helpers, and ``_log_diff`` remain for tests,
label-corpus tooling, and future engine-to-engine comparisons via
``comparator.compare`` → ``ike2_shadow_diffs``. The legacy-specific
``run_legacy_diff`` / ``legacy_external_verdict`` callers are gone with
``ComplianceEngine``.
"""
import logging
import sys
from types import SimpleNamespace

from core.knowledge.ike2 import input_layer, resolver
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external

logger = logging.getLogger(__name__)

SOURCE_CHAT = "chat"
SOURCE_API_COMPLIANCE = "api_evaluate_compliance"
SOURCE_API_PRODUCT = "api_evaluate_product"
SOURCE_TEST = "test"


def _interpreter_finalizing() -> bool:
    """True when Python is in teardown and background work must stop."""
    return bool(getattr(sys, "is_finalizing", lambda: False)())


def _profile_from_restriction_ids(restriction_ids):
    # Default medical severity so may_contain/trace triggers FAIL (not WARN).
    return SimpleNamespace(
        restrictions={rid: "medical" for rid in (restriction_ids or [])}
    )


def _resolve_compliance_inputs(
    raw_ingredients,
    region,
    *,
    decomposed_atoms=None,
):
    inputs = []
    if decomposed_atoms is not None:
        for atom in decomposed_atoms:
            resolved = resolver.resolve(atom.name, region)
            inputs.append(
                to_compliance_input(
                    resolved,
                    trace=atom.trace,
                    may_contain=atom.may_contain,
                    query_atom=atom.name,
                )
            )
    else:
        for raw in raw_ingredients or []:
            for atom in input_layer.parse_atoms(raw):
                resolved = resolver.resolve(atom.name, region)
                inputs.append(
                    to_compliance_input(
                        resolved,
                        trace=atom.trace,
                        may_contain=atom.may_contain,
                        query_atom=atom.name,
                    )
                )
    return inputs


def flags_from_compliance_inputs(inputs) -> list[dict]:
    """Flatten ComplianceInput / TruthAnchor-like objects to flag dicts for compare()."""
    out = []
    for inp in inputs or []:
        flags = dict(getattr(inp, "flags", None) or {})
        # alcohol_role lives on ComplianceInput, not always inside flags
        role = getattr(inp, "alcohol_role", None)
        if role is not None and "alcohol_role" not in flags:
            flags["alcohol_role"] = role
        out.append(flags)
    return out


def ike2_external_verdict(
    raw_ingredients,
    restriction_ids,
    region,
    rules=None,
    *,
    decomposed_atoms=None,
) -> str:
    """Run the IKE-2 pipeline end to end and return the external 3-tier verdict."""
    profile = _profile_from_restriction_ids(restriction_ids)
    active_rules = rules if rules is not None else rules_module.load_rules()
    inputs = _resolve_compliance_inputs(
        raw_ingredients, region, decomposed_atoms=decomposed_atoms
    )
    result = evaluate(inputs, profile, active_rules)
    return to_external(result.verdict)


def _log_diff(diff) -> None:
    """Persist a comparator diff row to ``ike2_shadow_diffs`` (fail-safe)."""
    if _interpreter_finalizing():
        logger.debug("Skipping _log_diff: interpreter is finalizing")
        return

    from core.knowledge.ingredient_db import get_supabase_config

    cfg = get_supabase_config()
    if not cfg:
        return
    from supabase import create_client

    payload = {
        "raw_input": diff.get("raw_input"),
        "legacy_verdict": diff.get("legacy_verdict"),
        "ike2_verdict": diff.get("ike2_verdict"),
        "match": diff.get("match"),
        "false_safe_regression": diff.get("false_safe_regression"),
        "source_route": diff.get("source_route"),
        "restriction_ids": diff.get("restriction_ids") or [],
    }
    try:
        create_client(cfg.url, cfg.key).table("ike2_shadow_diffs").insert(payload).execute()
    except Exception:
        logger.warning("IKE-2 shadow diff insert failed; comparison was logged", exc_info=True)
