"""IKE-2 restriction rules: the canonical seed plus the DB -> compliance bridge.

``ike2_restriction_rules`` stores rows as ``(category, field, operator, value,
action, min_knowledge_state, ...)``. ``compliance.evaluate`` instead reads a rule
as ``restriction``, ``kind``, optional ``trigger_flag`` / ``match_value``, ``action``,
and ``min_knowledge_state``. This module is the single place that maps one to the
other, and the single source of truth for what IKE-2 deterministically enforces.
"""
import json
from types import SimpleNamespace

# The field the alcohol rule keys off (compliance treats it specially).
ALCOHOL_FIELD = "alcohol_role"

# Boolean flag columns on ike2_ingredient_groups a rule may legitimately trigger
# on. A rule whose field is NOT here would silently never fire -> false-SAFE, so
# the rules test asserts every seeded flag rule names a column in this set.
VALID_FLAG_COLUMNS = frozenset({
    "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
    "bee_product",
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "peanut_source", "tree_nut_source", "fish_source", "shellfish_source",
    "mustard_source", "celery_source", "lupin_source", "sulphite_source",
    "root_vegetable", "onion_source", "garlic_source", "fermented",
})

_SAFETY = "AUTO_CLASSIFIED"   # allergy + medical: assert only when well-classified
_PREF = "DISCOVERED"          # lifestyle/preference: lower bar to assert
_REL = "DISCOVERED"           # religious diets: same bar as preference

# category == profile restriction id (data/restrictions.json); field == group column
# or composite (meat_fish_derived, alcohol_content, animal_species).
RULE_SEED = [
    # --- allergens (safety) -------------------------------------------------
    {"category": "peanut_allergy", "field": "peanut_source", "min_knowledge_state": _SAFETY},
    {"category": "tree_nut_allergy", "field": "tree_nut_source", "min_knowledge_state": _SAFETY},
    {"category": "soy_allergy", "field": "soy_source", "min_knowledge_state": _SAFETY},
    {"category": "sesame_allergy", "field": "sesame_source", "min_knowledge_state": _SAFETY},
    {"category": "fish_allergy", "field": "fish_source", "min_knowledge_state": _SAFETY},
    {"category": "shellfish_allergy", "field": "shellfish_source", "min_knowledge_state": _SAFETY},
    {"category": "mustard_allergy", "field": "mustard_source", "min_knowledge_state": _SAFETY},
    {"category": "lupin_allergy", "field": "lupin_source", "min_knowledge_state": _SAFETY},
    {"category": "celery_allergy", "field": "celery_source", "min_knowledge_state": _SAFETY},
    {"category": "onion_allergy", "field": "onion_source", "min_knowledge_state": _SAFETY},
    {"category": "garlic_allergy", "field": "garlic_source", "min_knowledge_state": _SAFETY},
    # --- medical ------------------------------------------------------------
    {"category": "gluten_free", "field": "gluten_source", "min_knowledge_state": _SAFETY},
    {"category": "celiac_strict", "field": "gluten_source", "min_knowledge_state": _SAFETY},
    {"category": "lactose_free", "field": "dairy_source", "min_knowledge_state": _SAFETY},
    {"category": "dairy_free", "field": "dairy_source", "min_knowledge_state": _SAFETY},
    {"category": "egg_free", "field": "egg_source", "min_knowledge_state": _SAFETY},
    {"category": "sulfite_sensitive", "field": "sulphite_source", "min_knowledge_state": _SAFETY},
    # --- lifestyle / preference --------------------------------------------
    {"category": "vegan", "field": "animal_origin", "min_knowledge_state": _PREF},
    {"category": "no_insect_derived", "field": "insect_derived", "min_knowledge_state": _PREF},
    {"category": "no_onion", "field": "onion_source", "min_knowledge_state": _PREF},
    {"category": "no_garlic", "field": "garlic_source", "min_knowledge_state": _PREF},
    {"category": "no_alcohol", "field": ALCOHOL_FIELD, "operator": "ne", "value": "none", "min_knowledge_state": _PREF},
    # --- religious / multi-field (data/restrictions.json semantics) ---------
    {"category": "halal", "field": "alcohol_content", "operator": "gt", "value": "0", "min_knowledge_state": _REL},
    {"category": "halal", "field": "animal_species", "operator": "eq", "value": "pig", "min_knowledge_state": _REL},
    {"category": "halal", "field": "insect_derived", "min_knowledge_state": _REL},
    {"category": "kosher", "field": "animal_species", "operator": "in_list", "value": '["pig","shellfish"]', "min_knowledge_state": _REL},
    {"category": "kosher", "field": "shellfish_source", "min_knowledge_state": _REL},
    {"category": "kosher", "field": "insect_derived", "min_knowledge_state": _REL},
    {"category": "hindu_vegetarian", "field": "meat_fish_derived", "min_knowledge_state": _REL},
    {"category": "hindu_vegetarian", "field": "egg_source", "min_knowledge_state": _REL},
    # Insect dyes/shellac are not vegetarian; honey stays via bee_product (not insect_derived).
    {"category": "hindu_vegetarian", "field": "insect_derived", "min_knowledge_state": _REL},
    {"category": "hindu_non_vegetarian", "field": "animal_species", "operator": "in_list", "value": '["cow","pig"]', "min_knowledge_state": _REL},
    {"category": "hindu_non_vegetarian", "field": "insect_derived", "min_knowledge_state": _REL},
    {"category": "jain", "field": "meat_fish_derived", "min_knowledge_state": _REL},
    {"category": "jain", "field": "egg_source", "min_knowledge_state": _REL},
    {"category": "jain", "field": "insect_derived", "min_knowledge_state": _REL},
    {"category": "jain", "field": "bee_product", "min_knowledge_state": _REL},
    {"category": "jain", "field": "root_vegetable", "min_knowledge_state": _REL},
    {"category": "jain", "field": "alcohol_content", "operator": "gt", "value": "0", "min_knowledge_state": _REL},
    {"category": "jain", "field": "onion_source", "min_knowledge_state": _REL},
    {"category": "jain", "field": "garlic_source", "min_knowledge_state": _REL},
    {"category": "jain", "field": "fermented", "action": "WARN", "min_knowledge_state": _REL},
    {"category": "jain", "field": "fungal", "min_knowledge_state": _REL},
    {"category": "vegetarian", "field": "meat_fish_derived", "min_knowledge_state": _PREF},
    {"category": "vegetarian", "field": "insect_derived", "min_knowledge_state": _PREF},
    {"category": "lacto_vegetarian", "field": "meat_fish_derived", "min_knowledge_state": _PREF},
    {"category": "lacto_vegetarian", "field": "egg_source", "min_knowledge_state": _PREF},
    {"category": "lacto_vegetarian", "field": "insect_derived", "min_knowledge_state": _PREF},
    {"category": "ovo_vegetarian", "field": "meat_fish_derived", "min_knowledge_state": _PREF},
    {"category": "ovo_vegetarian", "field": "dairy_source", "min_knowledge_state": _PREF},
    {"category": "ovo_vegetarian", "field": "insect_derived", "min_knowledge_state": _PREF},
    # Land meat only — fish/shellfish allowed. Enumerating species missed turkey/duck/etc.
    {"category": "pescatarian", "field": "meat_land_derived", "min_knowledge_state": _PREF},
]

# Restrictions IKE-2 claims to enforce. The rules test asserts the seed covers
# exactly this set, so dropping a seed row is caught.
SUPPORTED_RESTRICTIONS = frozenset(row["category"] for row in RULE_SEED)


def _parse_value(raw):
    if raw is None:
        return None
    if isinstance(raw, (bool, int, float, list)):
        return raw
    s = str(raw).strip()
    if s == "true":
        return True
    if s == "false":
        return False
    if s.startswith("["):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return s


def _rule_kind(field: str, operator: str) -> str:
    if field == ALCOHOL_FIELD:
        return "alcohol"
    if field == "meat_fish_derived":
        return "meat_fish_derived"
    if field == "meat_land_derived":
        return "meat_land_derived"
    if field == "alcohol_content":
        return "alcohol_content"
    if field == "animal_species":
        if operator in ("in_list", "in"):
            return "species_in_list"
        return "species_match"
    return "flag"


def _to_rule(row) -> SimpleNamespace:
    """Map a DB-shaped row (dict or attr object) to the compliance rule shape."""
    def field(name, default=None):
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)

    trigger = field("field")
    operator = field("operator", "eq")
    kind = _rule_kind(trigger, operator)
    value = _parse_value(field("value", "true" if kind == "flag" else None))

    return SimpleNamespace(
        restriction=field("category"),
        kind=kind,
        trigger_flag=trigger if kind == "flag" else None,
        match_value=value,
        action=field("action", "FAIL"),
        min_knowledge_state=field("min_knowledge_state", "AUTO_CLASSIFIED"),
    )


def seeded_rules():
    """The canonical rule set as compliance objects, with no DB dependency."""
    return [_to_rule(row) for row in RULE_SEED]


def load_rules(client=None):
    """Load active rules from ``ike2_restriction_rules`` as compliance objects.

    Falls back to the canonical in-code seed if the DB is unreachable, so a
    missing/empty table can never silently strip every rule (which the coverage
    guard would then turn into a wall of UNCERTAIN).

    Invalid ``field`` values (typos) are dropped with a warning so a bad DB row
    cannot silently never-fire and false-SAFE an entire allergen restriction.
    """
    import logging

    log = logging.getLogger(__name__)

    if client is None:
        from core.knowledge.ingredient_db import get_supabase_config

        cfg = get_supabase_config()
        if not cfg:
            return seeded_rules()
        from supabase import create_client

        client = create_client(cfg.url, cfg.key)

    try:
        rows = client.table("ike2_restriction_rules").select("*").execute().data
    except Exception:
        return seeded_rules()
    if not rows:
        return seeded_rules()

    out = []
    for r in rows:
        field = r.get("field") if isinstance(r, dict) else getattr(r, "field", None)
        # Composites + alcohol + species are valid non-column fields.
        if field not in VALID_FLAG_COLUMNS and field not in (
            ALCOHOL_FIELD,
            "meat_fish_derived",
            "meat_land_derived",
            "alcohol_content",
            "animal_species",
        ):
            log.warning(
                "IKE2 dropping restriction rule with unknown field %r (category=%r)",
                field,
                r.get("category") if isinstance(r, dict) else getattr(r, "category", None),
            )
            continue
        out.append(_to_rule(r))
    return out or seeded_rules()
