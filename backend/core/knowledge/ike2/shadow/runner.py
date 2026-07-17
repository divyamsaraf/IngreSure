"""Legacy diff runner.

IKE-2 is the primary pipeline (input -> resolve -> seam -> compliance); the
legacy engine now runs only for comparison. Every divergence between the two
is recorded in ``ike2_shadow_diffs``. This path is strictly observational and
is wrapped so it can never raise into or slow a failure onto the primary
result, and it always runs -- there is no mode gate.
"""
import logging
import sys
from types import SimpleNamespace

from core.knowledge.ike2 import input_layer, resolver
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.shadow.comparator import compare
from core.knowledge.ike2.verdict import to_external

logger = logging.getLogger(__name__)


def _interpreter_finalizing() -> bool:
    """True when Python is in teardown and background work must stop."""
    return bool(getattr(sys, "is_finalizing", lambda: False)())


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


def legacy_external_verdict(
    raw_ingredients,
    restriction_ids,
    region,
    *,
    decomposed_atoms=None,
) -> str:
    """Run the legacy engine and return its external 3-tier verdict.

    ``region`` is accepted for interface symmetry with ``ike2_external_verdict``;
    the legacy engine does not use it. ``use_api_fallback=False`` keeps this
    deterministic and network-free -- this path is diff-only, never user-facing.

    Calls ``ComplianceEngine`` directly instead of going through
    ``core.bridge.run_new_engine_chat``: once bridge's chat entrypoint is
    IKE-2-only, routing through it here would compare IKE-2 to itself.
    """
    from core.bridge import preprocess_ingredient_list
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.normalization.normalizer import substance_key

    if decomposed_atoms is not None:
        atomic_names = [atom.name for atom in decomposed_atoms]
        trace_keys = {atom.name for atom in decomposed_atoms if atom.trace}
        display_by_canonical = {}
        for atom in decomposed_atoms:
            display_by_canonical.setdefault(substance_key(atom.name), atom.name)
            display_by_canonical.setdefault(atom.name.lower().strip(), atom.name)
    else:
        atomic_names, trace_keys, display_by_canonical = preprocess_ingredient_list(
            raw_ingredients
        )

    verdict = ComplianceEngine().evaluate(
        atomic_names,
        restriction_ids=restriction_ids,
        trace_ingredient_keys=trace_keys or None,
        use_api_fallback=False,
        input_display_map=display_by_canonical or None,
    )
    return verdict.status.value


def _log_diff(diff) -> None:
    if _interpreter_finalizing():
        logger.debug("Skipping _log_diff: interpreter is finalizing")
        return

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


def run_legacy_diff(
    raw_ingredients,
    restriction_ids,
    region,
    primary_verdict,
    *,
    decomposed_atoms=None,
    writer=None,
):
    """Run the legacy engine and diff it against the already-computed primary
    (IKE-2) verdict. Always runs -- no mode gate.

    Fail-safe: returns None on any error and never propagates, so the
    caller's primary result is unaffected. Returns the diff dict when the
    comparison ran.
    """
    # During interpreter shutdown, thread-pool submissions from downstream libs
    # can raise RuntimeError ("cannot schedule new futures..."). Legacy diff is
    # observational only, so skip entirely in that phase.
    if _interpreter_finalizing():
        logger.info("IKE-2 legacy diff skipped during interpreter finalization")
        return None

    try:
        primary_ext = getattr(primary_verdict, "value", primary_verdict)
        legacy_ext = legacy_external_verdict(
            raw_ingredients,
            restriction_ids,
            region,
            decomposed_atoms=decomposed_atoms,
        )
        raw_input = ", ".join(raw_ingredients or [])
        diff = compare(legacy_ext, primary_ext, raw_input)
        logger.info(
            "IKE2_DIFF legacy=%s primary=%s match=%s false_safe_regression=%s "
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
    except RuntimeError as exc:
        # Shutdown race: downstream code may try to submit futures while Python
        # is finalizing. Diff is observational only, so swallow quietly.
        if "cannot schedule new futures after interpreter shutdown" in str(exc).lower():
            logger.info("IKE-2 legacy diff skipped during interpreter shutdown race")
            return None
        logger.warning("IKE-2 legacy diff failed; primary result unaffected", exc_info=True)
        return None
    except Exception:  # legacy diff must never break or slow-fail the primary path
        logger.warning("IKE-2 legacy diff failed; primary result unaffected", exc_info=True)
        return None
