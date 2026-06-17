"""Safety regression: a bulk-mapped record must never resolve to SAFE for the
user it endangers. These guard the two false-SAFE adapter bugs (nut_source fold,
unmapped alcohol_role) at the verdict level, not just the column level."""
from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.verdict import Verdict


def _resolved_from_row(row):
    """Build the resolved object compliance expects from a mapped group row,
    as a trusted, classified ingredient (the most dangerous case for false-SAFE)."""
    flags = {f: row[f] for f in BOOL_FLAGS}
    flags["alcohol_role"] = row["alcohol_role"]
    return SimpleNamespace(
        canonical_name=row["canonical_name"],
        flags=flags,
        knowledge_state=row["knowledge_state"],
        trusted=True,
        verdict_cap=row.get("verdict_cap"),
        alcohol_role=row["alcohol_role"],
        trace=False,
    )


def _profile(restriction, severity="medical"):
    return SimpleNamespace(restrictions={restriction: severity})


_PEANUT_RULE = SimpleNamespace(
    restriction="peanut", kind="flag", trigger_flag="peanut_source",
    min_knowledge_state="UNCLASSIFIED",
)
_ALCOHOL_RULE = SimpleNamespace(
    restriction="alcohol", kind="alcohol", trigger_flag=None,
    min_knowledge_state="UNCLASSIFIED",
)


def _raw(**over):
    base = {"canonical_name": "x", "aliases": ["x"], "regions": ["Global"]}
    base.update(over)
    return base


def test_peanut_product_is_never_safe_for_peanut_allergy():
    row, _ = map_record(_raw(canonical_name="peanut butter", nut_source="peanut butter, creamy"),
                        "usda", "AUTO_CLASSIFIED")
    result = evaluate([_resolved_from_row(row)], _profile("peanut"), [_PEANUT_RULE])
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.FAIL


def test_ambiguous_nut_is_never_safe_for_peanut_allergy():
    row, _ = map_record(_raw(canonical_name="nut blend", nut_source="mixed unidentified nut blend"),
                        "usda", "AUTO_CLASSIFIED")
    result = evaluate([_resolved_from_row(row)], _profile("peanut"), [_PEANUT_RULE])
    assert result.verdict != Verdict.SAFE


def test_alcohol_ingredient_is_never_safe_for_alcohol_restriction():
    row, _ = map_record(_raw(canonical_name="cooking wine", alcohol_content=11.0),
                        "usda", "AUTO_CLASSIFIED")
    result = evaluate([_resolved_from_row(row)], _profile("alcohol"), [_ALCOHOL_RULE])
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.FAIL
