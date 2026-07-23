from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Mapping

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import commit_promotion
from core.normalization.normalizer import normalize_ingredient_key


def build_promote_entry(cand: InductionCandidate) -> dict[str, Any]:
    induction = {
        "safety_class": cand.safety_class,
        "frequency": cand.frequency,
        "miss_class": cand.miss_class,
        "proposal_kind": cand.proposal_kind,
        "provenance": dict(cand.provenance),
    }
    if cand.proposal_kind == "variant_alias":
        alias = normalize_ingredient_key(cand.raw)
        canon = normalize_ingredient_key(cand.canonical or "")
        return {
            "candidate_key": candidate_key(alias, canon),
            "payload": {
                "write_kind": "variant_alias",
                "alias": alias,
                "canonical": canon,
                "induction": induction,
                "inverse": {"write_kind": "variant_alias", "alias": alias},
            },
        }
    canon = normalize_ingredient_key(cand.canonical or cand.raw)
    return {
        "candidate_key": candidate_key(canon, canon),
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": canon,
            "role": cand.role,
            "flags": {},
            "induction": induction,
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": canon,
                "prior_role": None,
                "role_patch_only": True,
            },
        },
    }


def submit_induced(
    cand: InductionCandidate,
    *,
    ledger: PromoteLedger,
    ontology_path: Path,
    aliases_path: Path,
    ontology: Mapping[str, Any],
    reviewer_id: str,
    approval_rationale: str,
    decision: Literal["accept", "reject"],
) -> dict[str, Any] | None:
    entry = build_promote_entry(cand)
    if decision != "accept":
        return ledger.append_non_promotable(
            candidate_key=entry["candidate_key"],
            rule_id="induction_reviewer_reject",
            source="phase2b_induction",
            reason="reviewer_reject",
            payload={"induction": entry["payload"]["induction"]},
        )

    name = cand.canonical or cand.raw
    gate = decide_promote(
        candidate_key=entry["candidate_key"],
        candidate_name=name,
        flags=cand.flags,
        ledger=ledger,
        ontology=ontology,
    )
    if gate.action == "rejected":
        return None

    # Structural force-human: never auto=True, even if gate.action == auto_promote.
    return commit_promotion(
        entry,
        ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        rule_id=gate.rule_id,
        source="phase2b_induction",
        auto=False,
        reviewer_id=reviewer_id,
        approval_rationale=approval_rationale,
        candidate_key=entry["candidate_key"],
    )
