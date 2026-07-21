"""Diet/allergen policy matrix: catch honey-class and processed-food false verdicts."""
from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
from core.models.user_profile import UserProfile
from core.models.verdict import VerdictStatus
from core.parsing.label_decomposer import decompose_label
from core.response_composer import build_ingredient_audit_payload


def _profile(diet="No rules", allergens=None):
    return UserProfile(
        user_id="matrix",
        dietary_preference=diet,
        allergens=allergens or [],
        lifestyle=[],
    )


def _status(diet, ings, allergens=None):
    p = _profile(diet, allergens)
    rids = user_profile_model_to_restriction_ids(p)
    return run_new_engine_chat(
        ings, user_profile=p, restriction_ids=rids, use_api_fallback=False
    )


def _bucket(diet, ing, allergens=None):
    p = _profile(diet, allergens)
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(
        [ing], user_profile=p, restriction_ids=rids, use_api_fallback=False
    )
    payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=[ing])
    for g in payload.get("groups") or []:
        for i in g.get("items") or []:
            name = (i.get("name") or "").lower()
            if ing.lower() in name or name in ing.lower() or ing.lower().split()[0] in name:
                return g["status"], v
    # renamed (e.g. natural flavors) — use first non-empty group
    for g in payload.get("groups") or []:
        if g.get("items"):
            return g["status"], v
    return None, v


# --- Honey is animal (vegan/Jain) but allowed for Halal/Kosher/Hindu ---

def test_honey_safe_for_diets_that_allow_it():
    for diet in ("Halal", "Kosher", "Hindu Vegetarian", "Hindu Non Veg", "Vegetarian", "Lacto Vegetarian"):
        status, v = _bucket(diet, "honey")
        assert status == "safe", (diet, status, v.triggered_ingredients)


def test_honey_avoid_for_vegan_and_jain():
    for diet in ("Vegan", "Jain"):
        status, _ = _bucket(diet, "honey")
        assert status == "avoid", diet


def test_insect_dyes_still_avoid_for_halal_kosher_jain():
    for diet in ("Halal", "Kosher", "Jain", "Vegan"):
        for term in ("carmine", "shellac"):
            status, _ = _bucket(diet, term)
            assert status == "avoid", (diet, term, status)


def test_insect_dyes_avoid_for_vegetarian_style_diets():
    """Carmine/shellac are insect-derived — not Safe for lacto-style vegetarian diets.
    Honey stays Safe (bee_product, not insect_derived)."""
    for diet in ("Hindu Vegetarian", "Vegetarian", "Lacto Vegetarian"):
        for term in ("carmine", "shellac"):
            status, _ = _bucket(diet, term)
            assert status == "avoid", (diet, term, status)
        status, _ = _bucket(diet, "honey")
        assert status == "safe", (diet, "honey", status)


# --- Cheese must not invent animal rennet ---

def test_cheese_does_not_expand_to_rennet():
    atoms = [a.name for a in decompose_label("cheese")]
    assert "rennet" not in atoms, atoms
    assert any("cheese" in a or a == "milk" for a in atoms) or atoms == ["cheese"]


def test_cheese_safe_for_lacto_style_diets():
    for diet in ("Vegetarian", "Lacto Vegetarian", "Hindu Vegetarian"):
        v = _status(diet, ["cheese"])
        assert v.status == VerdictStatus.SAFE, (diet, v.status, v.triggered_ingredients)


def test_explicit_rennet_still_avoid_for_vegetarian():
    v = _status("Vegetarian", ["rennet"])
    assert v.status == VerdictStatus.NOT_SAFE


# --- Pasta must not invent egg ---

def test_pasta_does_not_invent_egg():
    for term in ("pasta", "noodles", "spaghetti", "macaroni"):
        atoms = [a.name for a in decompose_label(term)]
        assert "egg" not in atoms, (term, atoms)


def test_pasta_safe_for_vegan():
    v = _status("Vegan", ["pasta"])
    assert v.status == VerdictStatus.SAFE, (v.status, v.triggered_ingredients)
    status, _ = _bucket("Vegan", "pasta")
    assert status == "safe", status


def test_mayonnaise_still_has_egg_for_vegan():
    atoms = [a.name for a in decompose_label("mayonnaise")]
    assert "egg" in atoms
    v = _status("Vegan", ["mayonnaise"])
    assert v.status == VerdictStatus.NOT_SAFE


# --- Yogurt should resolve as dairy, not unknown culture ---

def test_yogurt_safe_for_vegetarian_not_depends_on_culture():
    atoms = [a.name for a in decompose_label("yogurt")]
    assert "bacterial culture" not in atoms, atoms
    v = _status("Vegetarian", ["yogurt"])
    assert v.status == VerdictStatus.SAFE, (v.status, v.uncertain_ingredients)


# --- Allergen cores still hold ---

def test_allergen_cores():
    cases = [
        ("Peanut", "peanut", "avoid"),
        ("Peanut", "almond", "safe"),
        ("Tree nut", "almond", "avoid"),
        ("Tree nut", "peanut", "safe"),
        ("Fish", "tuna", "avoid"),
        ("Fish", "shrimp", "safe"),
        ("Shellfish", "shrimp", "avoid"),
        ("Milk", "milk", "avoid"),
        ("Egg", "egg", "avoid"),
    ]
    for alg, ing, want in cases:
        status, _ = _bucket("No rules", ing, allergens=[alg])
        assert status == want, (alg, ing, status)
