from typing import Optional

from core.knowledge.ike2 import truth_anchor
from core.knowledge.ike2.verdict import Verdict, aggregate

# Knowledge-state ranking for the C2 min_knowledge_state gate.
_KS_RANK = {
    "UNCLASSIFIED": 0,
    "DISCOVERED": 1,
    "AUTO_CLASSIFIED": 2,
    "CLASSIFIED": 3,
    "VERIFIED": 4,
    "LOCKED": 5,
}

# Restrictions that must not firm-SAFE when source-origin is ambiguous.
_VEGAN_RELIGIOUS = frozenset({
    "vegan", "halal", "kosher", "jain", "hindu_vegetarian", "hindu_non_vegetarian",
    "vegetarian", "lacto_vegetarian", "ovo_vegetarian", "pescatarian", "no_insect_derived",
})
_DAIRY_EGG = frozenset({"vegan", "dairy_free", "lactose_free", "egg_free"})
_HALAL_KOSHER = frozenset({"halal", "kosher"})

# Uncertainty phrases that are irrelevant to diet/allergen origin (do not cap SAFE).
_UNCERTAINTY_IRRELEVANT = (
    "pku",
    "banned_substance",
)


class ComplianceResult:
    """Holds the aggregate verdict plus the per-match breakdown.

    Compares equal to a bare ``Verdict`` (so callers can assert on the headline
    verdict directly) while still exposing ``.verdict`` and the detail lists.
    """

    def __init__(
        self,
        verdict: Verdict,
        matched_contains,
        matched_may_contain,
        caution_reasons,
        breakdown,
    ):
        self.verdict = verdict
        self.matched_contains = matched_contains
        self.matched_may_contain = matched_may_contain
        self.caution_reasons = caution_reasons
        self.breakdown = breakdown

    def __eq__(self, other):
        if isinstance(other, Verdict):
            return self.verdict == other
        if isinstance(other, ComplianceResult):
            return self.verdict == other.verdict
        return NotImplemented

    def __hash__(self):
        return hash(self.verdict)

    def __repr__(self):
        return f"ComplianceResult({self.verdict!r})"


def _uncertainty_flags(flags: dict) -> list[str]:
    raw = flags.get("uncertainty_flags") or []
    return [str(x) for x in raw]


def _flag_matches_any(flag: str, patterns: tuple[str, ...]) -> bool:
    fl = flag.lower()
    return any(p in fl for p in patterns)


def _uncertainty_ceiling(restriction: str, flags: dict, animal_origin: bool) -> Optional[Verdict]:
    """Max verdict when a clean pass would otherwise be SAFE (fail-closed).

    Deny-by-default: any non-empty origin/source uncertainty on vegan/religious
    or dairy/egg restrictions caps to WARN. An allowlist of phrases previously
    failed open (e.g. ``mono_diglycerides`` on glycerin → false Safe for Jain).
    """
    uflags = _uncertainty_flags(flags)
    if not uflags:
        return None

    relevant = [
        f for f in uflags
        if not _flag_matches_any(f, _UNCERTAINTY_IRRELEVANT)
    ]
    if not relevant:
        return None

    if restriction in _VEGAN_RELIGIOUS or restriction in _DAIRY_EGG:
        return Verdict.WARN

    if restriction in _HALAL_KOSHER:
        if any(_flag_matches_any(f, ("halal_status_unverified",)) for f in relevant):
            return Verdict.WARN
        if animal_origin and any(_flag_matches_any(f, ("source_species_unspecified",)) for f in relevant):
            return Verdict.UNCERTAIN

    return None


# Allergen / insect / bee bits that Tier-2/DB often under-flags. Overlaying these
# True values is always safe (false-Avoid >> false-SAFE). Do NOT blindly overlay
# animal_origin — E910 resolves to canonical l-cysteine with verdict_cap WARN and
# animal_origin False; a separate blunt "l-cysteine" LOCKED fact has animal_origin
# True and would turn deliberate Depends into false Avoid.
_OVERLAY_SAFETY_TRUE = frozenset({
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "peanut_source", "tree_nut_source", "fish_source", "shellfish_source",
    "mustard_source", "celery_source", "lupin_source", "sulphite_source",
    "insect_derived", "bee_product",
    "onion_source", "garlic_source", "root_vegetable",
})


def _effective_flags(r) -> dict:
    """C1: heal under-flagged Tier-2/DB rows from curated Tier-1 facts.

    Ontology/DB rows are often ``AUTO_CLASSIFIED`` and omit allergen bits
    (``fish_source`` false on tuna, missing ``bee_product`` on honey). Overlay
    True safety flags from LOCKED/VERIFIED Tier-1 by canonical name. Preserve
    deliberate origin uncertainty (verdict_cap / uncertainty_flags) so compounds
    like E910 stay Depends rather than false Avoid.
    """
    flags = dict(getattr(r, "flags", {}) or {})
    fact = truth_anchor.lookup(getattr(r, "canonical_name", "") or "")
    if fact is None or fact.knowledge_state not in ("LOCKED", "VERIFIED"):
        return flags

    uncertain = bool(flags.get("verdict_cap") or flags.get("uncertainty_flags"))
    for key, value in fact.flags.items():
        if not value:
            continue
        if key in _OVERLAY_SAFETY_TRUE:
            flags[key] = True
        elif key == "animal_origin" and not uncertain:
            flags[key] = True
    # Honey policy: Tier-1 bee_product must clear stale DB insect_derived=true.
    if fact.flags.get("bee_product"):
        flags["bee_product"] = True
        flags["insect_derived"] = False
        if not uncertain:
            flags["animal_origin"] = True
    return flags


def _ks_rank(state: str) -> int:
    return _KS_RANK.get(state or "UNCLASSIFIED", 0)


def _effective_knowledge_state(r) -> str:
    """Elevate row KS when a curated Tier-1 fact exists for the same canonical.

    Systemic class: DB/ontology rows stuck at DISCOVERED demote medical FAIL to
    Depends and clean SAFE to WARN, even when flags are correct. If Tier-1 has
    LOCKED/VERIFIED the ingredient, trust that curation for gating.
    """
    ks = getattr(r, "knowledge_state", None) or "UNCLASSIFIED"
    fact = truth_anchor.lookup(getattr(r, "canonical_name", "") or "")
    if fact is None or fact.knowledge_state not in ("LOCKED", "VERIFIED"):
        return ks
    if _ks_rank(fact.knowledge_state) > _ks_rank(ks):
        return fact.knowledge_state
    return ks


def _ks_gate_ok(knowledge_state: str, rule) -> bool:
    """C2: rule may only assert a definite verdict at/above its min state."""
    minimum = getattr(rule, "min_knowledge_state", "UNCLASSIFIED")
    return _ks_rank(knowledge_state) >= _ks_rank(minimum)


def _meat_fish_derived(flags: dict) -> bool:
    """Derived composite: meat/fish/shellfish, excluding dairy/egg/insect/bee products."""
    if (
        flags.get("dairy_source")
        or flags.get("egg_source")
        or flags.get("insect_derived")
        or flags.get("bee_product")
    ):
        return False
    if flags.get("animal_origin"):
        return True
    return bool(flags.get("fish_source") or flags.get("shellfish_source"))


def _meat_land_derived(flags: dict) -> bool:
    """Land-animal meat for pescatarian: animal origin that is not fish/shellfish/dairy/egg/bee."""
    if (
        flags.get("dairy_source")
        or flags.get("egg_source")
        or flags.get("insect_derived")
        or flags.get("bee_product")
        or flags.get("fish_source")
        or flags.get("shellfish_source")
    ):
        return False
    return bool(flags.get("animal_origin"))


def _field_value(flags: dict, field: str):
    if field == "meat_fish_derived":
        return _meat_fish_derived(flags)
    if field == "meat_land_derived":
        return _meat_land_derived(flags)
    return flags.get(field)


def _species_is_porcine(species) -> bool:
    """True for explicit pig species or mixed-source strings listing porcine (e.g. gelatin)."""
    if species is None:
        return False
    s = str(species).lower()
    return s == "pig" or "porcine" in s


def _species_trigger(flags: dict, rule) -> tuple[bool, bool]:
    """Return (triggered, species_unknown_cautious).

    When animal_origin is set but species is unknown, species-based rules must
    not silently pass (false-SAFE) -> cautious UNCERTAIN instead.
    """
    species = flags.get("animal_species")
    kind = getattr(rule, "kind", "flag")
    target = getattr(rule, "match_value", None)

    if kind == "species_in_list":
        allowed = target if isinstance(target, list) else [target]
        if species in allowed:
            return True, False
        if "pig" in allowed and _species_is_porcine(species):
            return True, False
    elif kind == "species_match":
        if target == "pig" and _species_is_porcine(species):
            return True, False
        if species == target:
            return True, False

    # Egg/dairy/insect/bee products are identified non-meat sources — not
    # "unknown cow/pig". Applying species-unknown caution here falsely
    # UNCERTAIN/Depends eggs on hindu_non_vegetarian (and similar species diets)
    # when they should SAFE.
    if (
        flags.get("egg_source")
        or flags.get("dairy_source")
        or flags.get("insect_derived")
        or flags.get("bee_product")
    ):
        return False, False

    if species in (None, "") and flags.get("animal_origin"):
        return True, True
    return False, False


def _rule_triggered(r, flags: dict, rule) -> tuple[bool, bool, Optional[str]]:
    """Evaluate whether a rule fires. Returns (triggered, species_unknown, role)."""
    kind = getattr(rule, "kind", "flag")

    if kind == "alcohol":
        role = getattr(r, "alcohol_role", None)
        triggered = role not in (None, "none", "")
        return triggered, False, role

    if kind in ("species_match", "species_in_list"):
        triggered, cautious = _species_trigger(flags, rule)
        return triggered, cautious, None

    if kind == "alcohol_content":
        content = flags.get("alcohol_content")
        threshold = getattr(rule, "match_value", 0)
        try:
            triggered = content is not None and float(content) > float(threshold)
        except (TypeError, ValueError):
            triggered = False
        return triggered, False, None

    if kind == "meat_fish_derived":
        return _meat_fish_derived(flags), False, None

    if kind == "meat_land_derived":
        return _meat_land_derived(flags), False, None

    # Boolean flag column. Explicit NULL means "never evaluated" → cautious
    # (UNCERTAIN), not verified-absent. Absent keys still mean False for sparse
    # curated facts that only store True bits.
    trigger_flag = getattr(rule, "trigger_flag", None)
    if not trigger_flag:
        return False, False, None
    if trigger_flag in flags and flags.get(trigger_flag) is None:
        return False, True, None
    return bool(flags.get(trigger_flag)), False, None


def _verdict_for(r, rule, severity: Optional[str]):
    """C3: one ingredient × one rule -> (verdict, triggered, trace, caution)."""
    flags = _effective_flags(r)
    severity = severity or "medical"  # unknown severity is treated conservatively
    trusted = bool(getattr(r, "trusted", False))
    cap = getattr(r, "verdict_cap", None) or flags.get("verdict_cap")
    trace = bool(getattr(r, "trace", False))
    may_contain = bool(getattr(r, "may_contain", False))
    is_minor = trace or may_contain
    restriction = getattr(rule, "restriction", "")

    triggered, species_unknown, role = _rule_triggered(r, flags, rule)
    caution = None

    # Untrusted resolutions may never drive Avoid or Safe -> always UNCERTAIN.
    if not trusted:
        return Verdict.UNCERTAIN, triggered, trace, caution

    if species_unknown:
        return Verdict.UNCERTAIN, triggered, trace, "inherent_uncertainty"

    # Base verdict from the trigger.
    if not triggered:
        base = Verdict.SAFE
    elif role is not None:  # alcohol
        base = Verdict.FAIL if role == "ingredient" else Verdict.WARN
    elif getattr(rule, "action", "FAIL") == "WARN":
        base = Verdict.WARN
    elif is_minor:
        base = Verdict.FAIL if severity == "medical" else Verdict.WARN
    else:  # definite contains
        base = Verdict.FAIL

    # Compound/ambiguous terms can never be definitive SAFE -> WARN.
    if cap == "WARN" and base == Verdict.SAFE:
        return Verdict.WARN, triggered, trace, "inherent_uncertainty"

    # Uncertainty flags cap diet-relevant clean passes.
    if base == Verdict.SAFE:
        ceiling = _uncertainty_ceiling(restriction, flags, bool(flags.get("animal_origin")))
        if ceiling is not None:
            return ceiling, triggered, trace, "inherent_uncertainty"

    # Use Tier-1-elevated KS so stale DISCOVERED DB rows cannot soft-fail safety.
    knowledge_state = _effective_knowledge_state(r)

    # A definite FAIL needs sufficient knowledge state to stand.
    if base == Verdict.FAIL and not _ks_gate_ok(knowledge_state, rule):
        return Verdict.UNCERTAIN, triggered, trace, "unverified_knowledge"

    # Conservative knowledge-state propagation on a clean pass.
    if base == Verdict.SAFE:
        if knowledge_state == "UNCLASSIFIED":
            return Verdict.UNCERTAIN, triggered, trace, "unverified_knowledge"
        if knowledge_state == "DISCOVERED":
            return Verdict.WARN, triggered, trace, "unverified_knowledge"

    return base, triggered, trace, caution


def evaluate(resolved, profile, rules) -> ComplianceResult:
    """C4: aggregate the most-severe verdict across all ingredients × rules."""
    restrictions = getattr(profile, "restrictions", {}) or {}
    verdicts = []
    matched_contains = []
    matched_may_contain = []
    caution_reasons = []
    breakdown = {}

    covered = set()
    for r in resolved:
        for rule in rules:
            if rule.restriction not in restrictions:
                continue
            covered.add(rule.restriction)
            severity = restrictions.get(rule.restriction)
            verdict, triggered, trace, caution = _verdict_for(r, rule, severity)
            verdicts.append(verdict)
            name = getattr(r, "canonical_name", "?")
            key = (name, rule.restriction)
            prev = breakdown.get(key)
            breakdown[key] = verdict if prev is None else max(prev, verdict)
            if triggered:
                minor = bool(getattr(r, "trace", False)) or bool(getattr(r, "may_contain", False))
                if minor:
                    matched_may_contain.append(name)
                elif verdict == Verdict.FAIL:
                    matched_contains.append(name)
            if verdict != Verdict.SAFE:
                caution_reasons.append(f"{rule.restriction}:{name}")
            if caution:
                caution_reasons.append(f"{caution}:{rule.restriction}:{name}")

    # Fail-closed coverage guard: a profile restriction with no matching rule was
    # never evaluated. It must not be silently dropped (which would let unrelated
    # passing restrictions yield SAFE) -> degrade to UNCERTAIN.
    for restriction in restrictions:
        if restriction not in covered:
            verdicts.append(Verdict.UNCERTAIN)
            caution_reasons.append(f"uncovered_restriction:{restriction}")

    return ComplianceResult(
        aggregate(verdicts),
        matched_contains,
        matched_may_contain,
        caution_reasons,
        breakdown,
    )
