"""Safety regression: a bulk-mapped record must never resolve to SAFE for the
user it endangers. These guard the two false-SAFE adapter bugs (nut_source fold,
unmapped alcohol_role) end-to-end through the REAL resolver -> seam -> compliance
path — the db store is faked (the established resolver-test pattern) so the
mapped GroupRow is the only thing under test, not Supabase."""
from types import SimpleNamespace

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict


def _evaluate_via_resolver(monkeypatch, raw, atom, profile, rules):
    """Map -> insert (faked db) -> real resolve() -> seam -> evaluate."""
    import core.knowledge.ike2.stores.db as db

    row, _ = map_record(raw, "usda", "AUTO_CLASSIFIED")
    group = SimpleNamespace(**row)  # db GroupRow: every column is a flat attribute
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "unique")
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: group)

    resolved = resolve(atom, region=None)
    return evaluate([to_compliance_input(resolved)], profile, rules)


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


def test_peanut_product_is_never_safe_for_peanut_allergy(monkeypatch):
    result = _evaluate_via_resolver(
        monkeypatch,
        _raw(canonical_name="peanut butter", nut_source="peanut butter, creamy"),
        atom="peanut butter",
        profile=_profile("peanut"),
        rules=[_PEANUT_RULE],
    )
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.FAIL


def test_ambiguous_nut_is_never_safe_for_peanut_allergy(monkeypatch):
    result = _evaluate_via_resolver(
        monkeypatch,
        _raw(canonical_name="nut blend", nut_source="mixed unidentified nut blend"),
        atom="nut blend",
        profile=_profile("peanut"),
        rules=[_PEANUT_RULE],
    )
    assert result.verdict != Verdict.SAFE


def test_alcohol_ingredient_is_never_safe_for_alcohol_restriction(monkeypatch):
    result = _evaluate_via_resolver(
        monkeypatch,
        _raw(canonical_name="cooking wine", alcohol_content=11.0),
        atom="cooking wine",
        profile=_profile("alcohol"),
        rules=[_ALCOHOL_RULE],
    )
    assert result.verdict != Verdict.SAFE
    assert result.verdict == Verdict.FAIL
