import re
from pathlib import Path
from types import SimpleNamespace

from core.knowledge.ike2 import rules
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase/migrations"
_ROW_COLUMNS = (
    "category",
    "field",
    "operator",
    "value",
    "action",
    "min_knowledge_state",
    "region",
)


def _canonical_seed_rows():
    """RULE_SEED the way seeded_rules() and the SQL table store a row.

    A missing operator is eq, a missing value is true, a missing action is
    FAIL, and region is null. Those are the defaults _to_rule applies.
    """
    rows = {}
    for row in rules.RULE_SEED:
        if "value" in row and row["value"] is not None:
            value = str(row["value"])
        else:
            value = "true"
        key = (row["category"], row["field"], None)
        rows[key] = {
            "category": row["category"],
            "field": row["field"],
            "operator": row.get("operator", "eq"),
            "value": value,
            "action": row.get("action", "FAIL"),
            "min_knowledge_state": row["min_knowledge_state"],
            "region": None,
        }
    return rows


def _split_sql_args(text):
    parts, buf, quoted = [], [], False
    for ch in text:
        if ch == "'":
            quoted = not quoted
            buf.append(ch)
        elif ch == "," and not quoted:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _sql_token(token):
    token = token.strip()
    if token.lower() == "null":
        return None
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1]
    return token


def _migration_rule_rows():
    """Replay insert/delete statements against ike2_restriction_rules in order."""
    rows = {}
    insert_re = re.compile(
        r"insert into public\.ike2_restriction_rules\s*\(([^)]+)\)\s*values\s*(.*?)\s*on conflict",
        re.I | re.S,
    )
    delete_re = re.compile(
        r"delete from public\.ike2_restriction_rules\s+where\s+(.+?);",
        re.I | re.S,
    )
    tuple_re = re.compile(r"\((?:[^)']|'[^']*')*\)")
    for path in sorted(_MIGRATIONS.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        if "ike2_restriction_rules" not in text:
            continue
        events = [("del", m.start(), m.group(1)) for m in delete_re.finditer(text)]
        events += [
            ("ins", m.start(), m.group(1), m.group(2)) for m in insert_re.finditer(text)
        ]
        for event in sorted(events, key=lambda item: item[1]):
            if event[0] == "del":
                cats = re.findall(r"category\s*=\s*'([^']+)'", event[2])
                fields = re.findall(r"field\s*=\s*'([^']+)'", event[2])
                for key in list(rows):
                    if cats and key[0] not in cats:
                        continue
                    if fields and key[1] not in fields:
                        continue
                    if cats or fields:
                        del rows[key]
                continue
            cols = [c.strip() for c in event[2].split(",")]
            body = re.sub(r"--.*?$", "", event[3], flags=re.M)
            for match in tuple_re.finditer(body):
                parts = [_sql_token(p) for p in _split_sql_args(match.group(0)[1:-1])]
                if len(parts) != len(cols):
                    continue
                rec = dict(zip(cols, parts))
                key = (rec["category"], rec["field"], rec.get("region"))
                rows[key] = {col: rec.get(col) for col in _ROW_COLUMNS}
    return rows


def test_seed_sql_covers_rule_seed():
    """Python seed and the migration-replayed table must match on every column.

    String presence of category/field is not enough: operator, value, action,
    min_knowledge_state, and region have to match too.
    """
    python_rows = _canonical_seed_rows()
    sql_rows = _migration_rule_rows()
    assert python_rows == sql_rows
    for row, rule in zip(rules.RULE_SEED, rules.seeded_rules(), strict=True):
        assert rule.restriction == row["category"]
        assert rule.action == row.get("action", "FAIL")
        assert rule.min_knowledge_state == row["min_knowledge_state"]


def _profile(**restrictions):
    return SimpleNamespace(restrictions=restrictions)


def _resolved(**flags):
    base = {
        "canonical_name": "x",
        "knowledge_state": "VERIFIED",
        "trusted": True,
        "verdict_cap": None,
        "alcohol_role": flags.get("alcohol_role", "none"),
        "trace": False,
    }
    return SimpleNamespace(flags=flags, **base)


def test_seed_covers_exactly_the_supported_restrictions():
    # Dropping (or sneaking in) a seed row is caught here.
    expected = {
        "peanut_allergy", "tree_nut_allergy", "soy_allergy", "sesame_allergy",
        "fish_allergy", "shellfish_allergy", "mustard_allergy", "lupin_allergy",
        "celery_allergy", "onion_allergy", "garlic_allergy",
        "gluten_free", "celiac_strict", "lactose_free", "dairy_free", "egg_free",
        "sulfite_sensitive",
        "vegan", "no_insect_derived", "no_onion", "no_garlic", "no_alcohol",
        "halal", "kosher", "hindu_vegetarian", "hindu_non_vegetarian", "jain",
        "vegetarian", "lacto_vegetarian", "ovo_vegetarian", "pescatarian",
    }
    assert rules.SUPPORTED_RESTRICTIONS == expected
    covered = {r.restriction for r in rules.seeded_rules()}
    for restriction in rules.SUPPORTED_RESTRICTIONS:
        assert restriction in covered


def test_every_flag_rule_targets_a_real_group_column():
    # A typo'd trigger_flag would silently never fire -> false-SAFE. Guard it.
    for rule in rules.seeded_rules():
        if rule.kind == "flag":
            assert rule.trigger_flag in rules.VALID_FLAG_COLUMNS


def test_alcohol_rule_is_kind_alcohol():
    alcohol = [r for r in rules.seeded_rules() if r.restriction == "no_alcohol"]
    assert len(alcohol) == 1
    assert alcohol[0].kind == "alcohol"
    assert alcohol[0].trigger_flag is None


def test_seeded_rules_flag_a_peanut_ingredient():
    r = _resolved(peanut_source=True)
    result = evaluate([r], _profile(peanut_allergy="medical"), rules.seeded_rules())
    assert result.verdict != Verdict.SAFE


def test_seeded_rules_pass_a_clean_ingredient():
    r = _resolved(animal_origin=False)
    result = evaluate([r], _profile(vegan="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE


# ---- multi-field religious / lifestyle rules --------------------------------
def test_halal_fails_on_pig():
    r = _resolved(animal_species="pig", animal_origin=True, insect_derived=False)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_halal_fails_on_unspecified_gelatin():
    """Generic gelatin lists porcine among possible sources; must not be halal-safe."""
    r = _resolved(
        canonical_name="gelatin",
        animal_species="bovine/porcine/fish depending on source",
        animal_origin=True,
        insect_derived=False,
    )
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_kosher_fails_on_unspecified_gelatin():
    r = _resolved(
        canonical_name="gelatin",
        animal_species="bovine/porcine/fish depending on source",
        animal_origin=True,
        insect_derived=False,
    )
    result = evaluate([r], _profile(kosher="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_halal_fails_on_alcohol_content():
    r = _resolved(alcohol_content=12.0, animal_origin=False)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_kosher_fails_on_shellfish_species():
    r = _resolved(animal_species="shellfish", animal_origin=True, fish_source=True)
    result = evaluate([r], _profile(kosher="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_jain_fails_on_root_vegetable():
    r = _resolved(root_vegetable=True, animal_origin=False)
    result = evaluate([r], _profile(jain="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_jain_fermented_warns_not_fails():
    r = _resolved(
        fermented=True, animal_origin=False, root_vegetable=False,
        onion_source=False, garlic_source=False, fungal=False,
    )
    result = evaluate([r], _profile(jain="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.WARN


def test_vegetarian_fails_on_fish_via_meat_fish_derived():
    r = _resolved(animal_origin=True, fish_source=True, dairy_source=False, egg_source=False)
    result = evaluate([r], _profile(vegetarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_lacto_vegetarian_allows_dairy_blocks_egg():
    dairy_ok = _resolved(animal_origin=True, dairy_source=True, egg_source=False)
    assert evaluate([dairy_ok], _profile(lacto_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.SAFE
    egg_bad = _resolved(animal_origin=True, egg_source=True, dairy_source=False)
    assert evaluate([egg_bad], _profile(lacto_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.FAIL


def test_ovo_vegetarian_allows_egg_blocks_dairy():
    egg_ok = _resolved(animal_origin=True, egg_source=True, dairy_source=False)
    assert evaluate([egg_ok], _profile(ovo_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.SAFE
    dairy_bad = _resolved(animal_origin=True, dairy_source=True, egg_source=False)
    assert evaluate([dairy_bad], _profile(ovo_vegetarian="preference"), rules.seeded_rules()).verdict == Verdict.FAIL


def test_pescatarian_fails_on_chicken():
    r = _resolved(animal_species="chicken", animal_origin=True)
    result = evaluate([r], _profile(pescatarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.FAIL


def test_pescatarian_allows_fish():
    r = _resolved(animal_species="fish", animal_origin=True, fish_source=True)
    result = evaluate([r], _profile(pescatarian="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE


def test_unknown_species_with_animal_origin_is_not_safe_for_halal():
    r = _resolved(animal_origin=True, animal_species=None)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict != Verdict.SAFE


def test_halal_covered_no_longer_uncertain():
    r = _resolved(animal_origin=False, insect_derived=False, alcohol_content=None)
    result = evaluate([r], _profile(halal="preference"), rules.seeded_rules())
    assert result.verdict == Verdict.SAFE
    assert not any("uncovered_restriction" in c for c in result.caution_reasons)


def test_load_rules_falls_back_to_seed_when_db_unreachable(monkeypatch):
    """Configured Supabase that is down must not break IKE-2 (fail-closed seed)."""

    class _BrokenTable:
        def select(self, *_args, **_kwargs):
            return self

        def execute(self):
            raise ConnectionError("connection refused")

    class _BrokenClient:
        def table(self, _name):
            return _BrokenTable()

    monkeypatch.setattr(rules, "seeded_rules", rules.seeded_rules)
    loaded = rules.load_rules(client=_BrokenClient())
    assert len(loaded) == len(rules.seeded_rules())
    assert {r.restriction for r in loaded} == rules.SUPPORTED_RESTRICTIONS
