"""
Bridge: map profile diet names to restriction_ids; run compliance engine for chat.
"""
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Dict, List, Any, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.user_profile import UserProfile

from core.knowledge.ike2 import input_layer as ike2_input_layer
from core.knowledge.ike2 import resolver as ike2_resolver
from core.knowledge.ike2 import rules as ike2_rules
from core.knowledge.ike2 import compliance as ike2_compliance
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict, to_external
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.parsing.ingredient_parser import preprocess_ingredients
from core.normalization.parser import flatten_ingredients
from core.normalization.normalizer import substance_key

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping dictionaries (single source of truth)
# ---------------------------------------------------------------------------

# Dietary preference (display name, lowered) -> restriction_id
# Covers both dietary and religious diets. Used for user profiles.
DIETARY_PREFERENCE_TO_RESTRICTION_ID: Dict[str, str] = {
    "jain": "jain",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "hindu veg": "hindu_vegetarian",
    "hindu vegetarian": "hindu_vegetarian",
    "hindu non vegetarian": "hindu_non_vegetarian",
    "hindu non veg": "hindu_non_vegetarian",
    "halal": "halal",
    "kosher": "kosher",
    "lacto vegetarian": "lacto_vegetarian",
    "ovo vegetarian": "ovo_vegetarian",
    "pescatarian": "pescatarian",
    "gluten-free": "gluten_free",
    "dairy-free": "dairy_free",
    "egg-free": "egg_free",
    # Underscore variants (from frontend/profile storage)
    "hindu_veg": "hindu_vegetarian",
    "hindu_vegetarian": "hindu_vegetarian",
    "hindu_non_veg": "hindu_non_vegetarian",
    "hindu_non_vegetarian": "hindu_non_vegetarian",
    "lacto_vegetarian": "lacto_vegetarian",
    "ovo_vegetarian": "ovo_vegetarian",
    "gluten_free": "gluten_free",
    "dairy_free": "dairy_free",
    "egg_free": "egg_free",
}

# Allergen profile key -> restriction_id
ALLERGEN_TO_RESTRICTION_ID: Dict[str, str] = {
    "peanut": "peanut_allergy",
    "peanuts": "peanut_allergy",
    "nut": "tree_nut_allergy",
    "nuts": "tree_nut_allergy",
    "tree_nut": "tree_nut_allergy",
    "tree_nuts": "tree_nut_allergy",
    "soy": "soy_allergy",
    "shellfish": "shellfish_allergy",
    "fish": "fish_allergy",
    "sesame": "sesame_allergy",
    "onion": "onion_allergy",
    "garlic": "garlic_allergy",
    "gluten": "gluten_free",
    "wheat": "gluten_free",
    "milk": "dairy_free",
    "dairy": "dairy_free",
    "egg": "egg_free",
    "eggs": "egg_free",
    "mustard": "mustard_allergy",
    "celery": "celery_allergy",
    "raisin": "raisin_allergy",
    "raisins": "raisin_allergy",
}

# Lifestyle flags -> restriction_id
LIFESTYLE_TO_RESTRICTION_ID: Dict[str, str] = {
    "no_onion": "no_onion",
    "no_garlic": "no_garlic",
    "no_alcohol": "no_alcohol",
    "no_insect_derived": "no_insect_derived",
    "no_palm_oil": "no_palm_oil",
    "no_artificial_colors": "no_artificial_colors",
    "no_gmos": "no_gmos",
    "no_seed_oils": "no_seed_oils",
    "keto": "keto",
    "paleo": "paleo",
}


def _normalize_key(s: str) -> str:
    return (s or "").lower().strip().replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Profile -> restriction_ids
# ---------------------------------------------------------------------------

def profile_to_restriction_ids(user_profile: Optional[Dict[str, Any]]) -> List[str]:
    """Build restriction_ids from userProfile dict (dietary_preference, allergens, lifestyle)."""
    if not user_profile:
        return []
    ids: List[str] = []
    seen: Set[str] = set()

    def _add(rid: str) -> None:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)

    pref = _normalize_key(user_profile.get("dietary_preference") or "")
    if pref and pref not in ("no_rules", "no rules"):
        rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(pref)
        if rid:
            _add(rid)

    for a in user_profile.get("allergens", []) or []:
        key = _normalize_key(str(a))
        rid = ALLERGEN_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    for v in user_profile.get("lifestyle", []) or []:
        key = _normalize_key(str(v))
        rid = LIFESTYLE_TO_RESTRICTION_ID.get(key) or DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    return ids


def user_profile_model_to_restriction_ids(profile: "UserProfile") -> List[str]:
    """Build restriction_ids from UserProfile model."""
    ids: List[str] = []
    seen: Set[str] = set()

    def _add(rid: str) -> None:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)

    # Primary dietary preference
    pref = (profile.dietary_preference or "no rules").lower().strip()
    if pref and pref != "no rules":
        rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(pref)
        if not rid:
            key = _normalize_key(pref)
            rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key) or LIFESTYLE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    # Allergens
    for a in profile.allergens or []:
        key = _normalize_key(str(a))
        rid = ALLERGEN_TO_RESTRICTION_ID.get(key) or LIFESTYLE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    # Lifestyle
    for v in profile.lifestyle or []:
        key = _normalize_key(str(v))
        rid = LIFESTYLE_TO_RESTRICTION_ID.get(key) or DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    return ids


# ---------------------------------------------------------------------------
# Ingredient preprocessing
# ---------------------------------------------------------------------------

def preprocess_ingredient_list(
    ingredients: List[str],
) -> Tuple[List[str], Set[str], Dict[str, str]]:
    """Preprocess ingredient strings into atomic names, trace keys, and display labels.

    display_by_canonical maps substance keys (e.g. carmine, gelatin) back to the
    user's original input (e.g. E120, E441) for audit card display.
    """
    flattened: List[str] = []
    trace_keys: Set[str] = set()
    display_by_canonical: Dict[str, str] = {}
    for s in ingredients:
        if not s or not str(s).strip():
            continue
        s = str(s).strip()
        items = preprocess_ingredients(s)
        for x in items:
            atoms = flatten_ingredients(x["name"])
            for a in atoms:
                flattened.append(a)
                sk = substance_key(a)
                display_by_canonical.setdefault(sk, s)
                display_by_canonical.setdefault(a.lower().strip(), s)
                if x.get("trace"):
                    trace_keys.add(a)
        if not items:
            atoms = flatten_ingredients(s)
            for a in atoms:
                flattened.append(a)
                sk = substance_key(a)
                display_by_canonical.setdefault(sk, s)
                display_by_canonical.setdefault(a.lower().strip(), s)
    return flattened, trace_keys, display_by_canonical


# ---------------------------------------------------------------------------
# IKE-2 result -> ComplianceVerdict mapper
# ---------------------------------------------------------------------------

# Sentinel key format for position-keyed display-map entries (used only for
# atoms IKE-2 could not resolve, where canonical_name is "" and therefore
# cannot itself be used as a lookup key). The NUL prefix keeps this namespace
# disjoint from real canonical/substance-key strings.
_UNRESOLVED_POS_KEY = "\x00pos:{}"


def map_ike2_to_compliance_verdict(
    result, inputs, *, ontology_version: str = "", input_display_map: dict | None = None
) -> ComplianceVerdict:
    """Map an IKE-2 ``ComplianceResult`` (+ its ``ComplianceInput`` list) to the
    external ``ComplianceVerdict`` shape. Status comes only from
    ``VerdictStatus(to_external(result.verdict))`` — never reimplemented here.

    ``input_display_map`` (canonical name / substance_key -> raw user input)
    lets the audit UI show what the user typed (e.g. "E120") instead of the
    resolved canonical ("carmine"). It is optional: IKE-2's ``ComplianceInput``
    carries no raw text on its own, so callers that resolve ingredients build
    this map themselves (see ``_run_ike2_compliance``).
    """
    status = VerdictStatus(to_external(result.verdict))

    triggered_ingredients = list(dict.fromkeys(result.matched_contains or []))
    informational_ingredients = list(dict.fromkeys(result.matched_may_contain or []))

    triggered_restrictions = []
    seen_restrictions = set()
    for (name, restriction), verdict in (result.breakdown or {}).items():
        if verdict == Verdict.SAFE:
            continue
        if name in triggered_ingredients and restriction not in seen_restrictions:
            seen_restrictions.add(restriction)
            triggered_restrictions.append(restriction)

    display_map = input_display_map or {}
    triggered_ingredient_to_input: Dict[str, str] = {}
    for canonical in triggered_ingredients:
        raw = display_map.get(canonical) or display_map.get(substance_key(canonical))
        if raw:
            triggered_ingredient_to_input[canonical] = raw

    uncertain_ingredients = []
    for idx, inp in enumerate(inputs or []):
        canonical_name = getattr(inp, "canonical_name", "") or ""
        is_uncertain = (
            not getattr(inp, "trusted", True)
            or getattr(inp, "knowledge_state", "") in ("UNCLASSIFIED", "DISCOVERED")
            or not canonical_name
        )
        if is_uncertain:
            # canonical_name is "" for unresolved atoms, so fall back to the
            # raw atom/input text (position-keyed) rather than the literal
            # "unknown" -- lets the audit exclude these from Safe by substance.
            raw = display_map.get(_UNRESOLVED_POS_KEY.format(idx))
            label = canonical_name or raw or "unknown"
            if label not in uncertain_ingredients:
                uncertain_ingredients.append(label)

    confidence_score = 1.0 if (status == VerdictStatus.SAFE and not uncertain_ingredients) else 0.0

    return ComplianceVerdict(
        status=status,
        triggered_restrictions=triggered_restrictions,
        triggered_ingredients=triggered_ingredients,
        triggered_ingredient_to_input=triggered_ingredient_to_input or None,
        uncertain_ingredients=uncertain_ingredients,
        informational_ingredients=informational_ingredients,
        confidence_score=confidence_score,
        ontology_version=ontology_version,
    )


# ---------------------------------------------------------------------------
# Engine runner (IKE-2 primary; never falls back to the legacy engine)
# ---------------------------------------------------------------------------

def _profile_from_restriction_ids(restriction_ids: Optional[List[str]]) -> SimpleNamespace:
    # Default medical severity so may_contain/trace triggers FAIL (not WARN).
    return SimpleNamespace(restrictions={rid: "medical" for rid in (restriction_ids or [])})


def _input_hash(ingredients: Optional[List[str]], restriction_ids: Optional[List[str]]) -> str:
    raw = "|".join(ingredients or []) + "::" + ",".join(sorted(restriction_ids or []))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _record_display(
    display_map: Dict[str, str], idx: int, canonical_name: str, raw_display: str
) -> None:
    """Record one atom's raw display text, keyed for later lookup by the mapper.

    Resolved atoms are keyed by canonical name (+ substance_key) so
    ``triggered_ingredient_to_input`` can look them up by canonical.
    Unresolved atoms (canonical_name == "") have no stable key of their own,
    so they're keyed by position instead (see ``_UNRESOLVED_POS_KEY``).
    """
    if canonical_name:
        display_map.setdefault(canonical_name, raw_display)
        sk = substance_key(canonical_name)
        if sk:
            display_map.setdefault(sk, raw_display)
    else:
        display_map[_UNRESOLVED_POS_KEY.format(idx)] = raw_display


def _run_ike2_compliance(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    prepared_decomposed: Optional[List[Any]] = None,
    region: Optional[str] = None,
) -> Tuple[Any, List[Any], Dict[str, str]]:
    """Run the IKE-2 pipeline (input -> resolve -> seam -> rules -> evaluate)
    and return the raw ``ComplianceResult``, its ``ComplianceInput`` list, and
    a display map (canonical/substance_key -> raw user input) for the mapper.

    Same pipeline as ``core.knowledge.ike2.shadow.runner.ike2_external_verdict``,
    kept separate because that module returns only the external status string
    while the chat path needs the full result to build a ``ComplianceVerdict``.
    """
    profile = _profile_from_restriction_ids(restriction_ids)
    active_rules = ike2_rules.load_rules()
    inputs = []
    display_map: Dict[str, str] = {}
    if prepared_decomposed is not None:
        for idx, atom in enumerate(prepared_decomposed):
            resolved = ike2_resolver.resolve(atom.name, region)
            ci = to_compliance_input(resolved, trace=atom.trace, may_contain=atom.may_contain)
            inputs.append(ci)
            # DecomposedItem carries no original display text (it's already
            # post-decompose), so atom.name is the best available display.
            _record_display(display_map, idx, ci.canonical_name, atom.name)
    else:
        idx = 0
        for raw in ingredients or []:
            for atom in ike2_input_layer.parse_atoms(raw):
                resolved = ike2_resolver.resolve(atom.name, region)
                ci = to_compliance_input(resolved, trace=atom.trace, may_contain=atom.may_contain)
                inputs.append(ci)
                _record_display(display_map, idx, ci.canonical_name, raw)
                idx += 1
    result = ike2_compliance.evaluate(inputs, profile, active_rules)
    return result, inputs, display_map


# Legacy shadow diff is observational only, so it is capped rather than left
# to run indefinitely -- a hung legacy call must not accumulate threads.
LEGACY_DIFF_TIMEOUT_SEC = 5

# Worker pool that actually runs the legacy diff. A second, small pool
# supervises each worker future with a timeout so the *request* thread never
# waits on either the legacy call or the timeout -- `_schedule_legacy_diff`
# only submits and returns.
_LEGACY_DIFF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="legacy-diff")
_LEGACY_DIFF_SUPERVISOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="legacy-diff-sv")


def _run_legacy_diff_job(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    primary_status: str,
    prepared_decomposed: Optional[List[Any]] = None,
) -> None:
    """Diff the legacy engine against the already-computed IKE-2 verdict.

    Runs on a background worker thread (see ``_schedule_legacy_diff``).
    Observational only; must never affect the primary result. Uses
    ``use_api_fallback=False`` inside ``run_legacy_diff`` to keep the diff
    deterministic and network-free.
    """
    from core.knowledge.ike2.shadow.runner import run_legacy_diff

    run_legacy_diff(
        ingredients,
        restriction_ids,
        None,
        primary_status,
        decomposed_atoms=prepared_decomposed,
    )


def _supervise_legacy_diff(future) -> None:
    """Wait (with timeout) for a legacy diff future, off the request thread.

    Runs on the supervisor pool. Never raises -- logs and moves on.
    """
    try:
        future.result(timeout=LEGACY_DIFF_TIMEOUT_SEC)
    except TimeoutError:
        future.cancel()
        logger.warning(
            "IKE-2 legacy diff exceeded %ss timeout; abandoning", LEGACY_DIFF_TIMEOUT_SEC
        )
    except Exception:
        logger.warning("IKE-2 legacy diff failed", exc_info=True)


def _schedule_legacy_diff(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    primary_status: str,
    prepared_decomposed: Optional[List[Any]] = None,
) -> None:
    """Fire-and-forget: submit the legacy diff to a background worker pool
    and return immediately. The request thread never blocks on the legacy
    engine or on the timeout that bounds it.
    """
    try:
        future = _LEGACY_DIFF_EXECUTOR.submit(
            _run_legacy_diff_job,
            ingredients,
            restriction_ids,
            primary_status,
            prepared_decomposed,
        )
        _LEGACY_DIFF_SUPERVISOR.submit(_supervise_legacy_diff, future)
    except Exception:
        logger.warning("IKE-2 legacy diff scheduling failed", exc_info=True)


def run_new_engine_chat(
    ingredients: List[str],
    user_profile: Optional[Any] = None,
    restriction_ids: Optional[List[str]] = None,
    profile_context: Optional[Dict[str, Any]] = None,
    use_api_fallback: bool = True,
    prepared_decomposed: Optional[List[Any]] = None,
) -> ComplianceVerdict:
    """Run compliance for chat. IKE-2 is the only source of the returned
    verdict; on any IKE-2 failure this fails closed to UNCERTAIN and never
    falls back to the legacy engine's result."""
    if restriction_ids is not None:
        rids = restriction_ids
    elif hasattr(user_profile, "dietary_preference"):
        rids = user_profile_model_to_restriction_ids(user_profile)
    else:
        rids = profile_to_restriction_ids(user_profile if isinstance(user_profile, dict) else None)

    try:
        ike2_output = _run_ike2_compliance(ingredients, rids, prepared_decomposed)
        if isinstance(ike2_output, ComplianceVerdict):
            verdict = ike2_output
        else:
            result, inputs, display_map = ike2_output
            verdict = map_ike2_to_compliance_verdict(
                result, inputs, input_display_map=display_map
            )
    except Exception:
        logger.exception(
            "IKE2_PRIMARY_FAILED input_hash=%s restriction_ids=%s",
            _input_hash(ingredients, rids), rids,
        )
        verdict = ComplianceVerdict(status=VerdictStatus.UNCERTAIN)

    _schedule_legacy_diff(ingredients, rids, verdict.status.value, prepared_decomposed)

    return verdict

