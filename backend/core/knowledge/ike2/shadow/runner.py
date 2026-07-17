"""Shadow-mode orchestrator.

When ``IKE2_MODE == 'shadow'`` the full IKE-2 pipeline (input -> resolve -> seam
-> compliance) runs alongside the legacy engine and every divergence is recorded
in ``ike2_shadow_diffs``. The legacy verdict is always what the user sees; this
path is strictly observational and is wrapped so it can never raise into or slow
a failure onto the legacy result.
"""
import logging
from types import SimpleNamespace

from core import config
from core.knowledge.ike2 import input_layer, resolver
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.shadow.comparator import compare
from core.knowledge.ike2.verdict import to_external

logger = logging.getLogger(__name__)


def _profile_from_restriction_ids(restriction_ids):
    # Default medical severity so may_contain/trace triggers FAIL (not WARN).
    return SimpleNamespace(
        restrictions={rid: "medical" for rid in (restriction_ids or [])}
    )


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
    inputs = []
    if decomposed_atoms is not None:
        for atom in decomposed_atoms:
            resolved = resolver.resolve(atom.name, region)
            inputs.append(
                to_compliance_input(
                    resolved, trace=atom.trace, may_contain=atom.may_contain
                )
            )
    else:
        for raw in raw_ingredients or []:
            for atom in input_layer.parse_atoms(raw):
                resolved = resolver.resolve(atom.name, region)
                inputs.append(
                    to_compliance_input(
                        resolved, trace=atom.trace, may_contain=atom.may_contain
                    )
                )
    result = evaluate(inputs, profile, active_rules)
    return to_external(result.verdict)


def _log_diff(diff) -> None:
    from core.knowledge.ingredient_db import get_supabase_config

    cfg = get_supabase_config()
    if not cfg:
        return
    from supabase import create_client

    try:
        create_client(cfg.url, cfg.key).table("ike2_shadow_diffs").insert(
            {
                "raw_input": diff["raw_input"],
                "legacy_verdict": diff["legacy_verdict"],
                "ike2_verdict": diff["ike2_verdict"],
                "match": diff["match"],
                "false_safe_regression": diff["false_safe_regression"],
            }
        ).execute()
    except Exception:
        logger.warning("IKE-2 shadow diff insert failed; comparison was logged", exc_info=True)


def run_shadow(
    raw_ingredients,
    restriction_ids,
    region,
    legacy_verdict,
    *,
    decomposed_atoms=None,
    writer=None,
):
    """Compare IKE-2 to legacy and record divergences. No-op unless mode=='shadow'.

    Fail-safe: returns None on any error and never propagates, so the user-facing
    legacy verdict is unaffected. Returns the diff dict when the comparison ran.
    """
    if config.IKE2_MODE != "shadow":
        return None
    try:
        legacy_ext = getattr(legacy_verdict, "value", legacy_verdict)
        ike2_ext = ike2_external_verdict(
            raw_ingredients,
            restriction_ids,
            region,
            decomposed_atoms=decomposed_atoms,
        )
        raw_input = ", ".join(raw_ingredients or [])
        diff = compare(legacy_ext, ike2_ext, raw_input)
        logger.info(
            "IKE2_SHADOW legacy=%s ike2=%s match=%s false_safe_regression=%s "
            "restriction_ids=%s ingredients=%s",
            diff["legacy_verdict"],
            diff["ike2_verdict"],
            diff["match"],
            diff["false_safe_regression"],
            restriction_ids,
            raw_input[:200] if raw_input else "",
        )
        if not diff["match"]:
            (writer or _log_diff)(diff)
        return diff
    except Exception:  # shadow must never break or slow-fail the legacy path
        logger.warning("IKE-2 shadow run failed; legacy unaffected", exc_info=True)
        return None
