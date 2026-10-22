"""Parse diet/allergy/lifestyle statements with confirm-before-change.

Unconfirmed restrictions may only *tighten* verdicts. Persistence and any
relaxation wait for confirmation (see core.pending_restrictions).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_CELIAC = re.compile(r"\bceliac\b|\bcoeliac\b", re.IGNORECASE)
_NOT_CELIAC = re.compile(r"\bnot\s+(?:a\s+)?(?:celiac|coeliac)\b", re.IGNORECASE)
_ALLERGIC = re.compile(
    r"\b(?:i(?:'m|\s+am)?|im)\s+allergic\s+to\s+([^.]+)",
    re.IGNORECASE,
)
_HAVE_ALLERGY = re.compile(
    r"\b(?:i\s+have)\s+(?:a\s+|an\s+)?([a-z\s-]+?)\s+allerg(?:y|ies)\b",
    re.IGNORECASE,
)
_LACTOSE = re.compile(r"\blactose[-\s]?intoleran", re.IGNORECASE)
_GLUTEN_SENSITIVE = re.compile(r"\bgluten[-\s]?sensitiv", re.IGNORECASE)
_USED_TO = re.compile(
    r"\b(?:used\s+to\s+be|no\s+longer(?:\s+am)?|i\s+was(?:\s+a)?)\s+(vegan|vegetarian|jain|halal|kosher)\b",
    re.IGNORECASE,
)
_GONE = re.compile(
    r"\b(?:allerg(?:y|ies)\s+is\s+gone|allerg(?:y|ies)\s+is\s+over|"
    r"(?:think|thought).{0,40}allerg(?:y|ies).{0,20}(?:gone|over|resolved))\b",
    re.IGNORECASE,
)
_TEMPORARY = re.compile(
    r"\b(?:just\s+for\s+(?:this\s+)?(?:week|month|today)|temporarily|for\s+now|"
    r"just\s+today|this\s+week|during\s+fasting|navratri|ramadan)\b",
    re.IGNORECASE,
)
_OTHER_SCOPE = re.compile(
    r"\b(?:for\s+my\s+(?:kid|child|son|daughter|partner|friend|husband|wife)|"
    r"someone\s+else|my\s+(?:kid|child|son|daughter)'s)\b",
    re.IGNORECASE,
)
_UNSUPPORTED = (
    ("keto", re.compile(r"\bketo(?:genic)?\b", re.IGNORECASE)),
    ("diabetic", re.compile(r"\bdiabet(?:es|ic)\b", re.IGNORECASE)),
    ("low_sodium", re.compile(r"\blow[-\s]?sodium\b|\blow[-\s]?salt\b", re.IGNORECASE)),
    ("organic", re.compile(r"\borganic\b", re.IGNORECASE)),
    ("low_fodmap", re.compile(r"\blow[-\s]?fodmap\b", re.IGNORECASE)),
)
_NOT_DIET = re.compile(
    r"\b(?:i(?:'m|\s+am)?|im)\s+not\s+(a\s+)?(vegan|vegetarian|jain|halal|kosher)\b",
    re.IGNORECASE,
)
_BARE_PLEASE = re.compile(
    r"^\s*(vegan|vegetarian|jain|halal|kosher)\s+please\b",
    re.IGNORECASE,
)
_DIET_DISPLAY = {
    "vegan": "Vegan",
    "vegetarian": "Vegetarian",
    "jain": "Jain",
    "halal": "Halal",
    "kosher": "Kosher",
    "gluten_free": "Gluten-Free",
    "dairy_free": "Dairy-Free",
}
_DIET_TO_RID = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "jain": "jain",
    "halal": "halal",
    "kosher": "kosher",
}

# Comma/list fragments that must all be captured (spec B04).
_FRAGMENT_DIETS = (
    (re.compile(r"\bvegan\b", re.I), "vegan", "Vegan"),
    (re.compile(r"\bvegetarian\b|\bveggie\b", re.I), "vegetarian", "Vegetarian"),
    (re.compile(r"\bhalal\b", re.I), "halal", "Halal"),
    (re.compile(r"\bjain\b", re.I), "jain", "Jain"),
    (re.compile(r"\bgluten[-\s]?free\b", re.I), "gluten_free", "Gluten-Free"),
    (re.compile(r"\bdairy[-\s]?free\b", re.I), "dairy_free", "Dairy-Free"),
)
_FRAGMENT_ALLERGENS = (
    (re.compile(r"\bno\s+nuts?\b|\bnut[-\s]?free\b", re.I), "nuts"),
    (re.compile(r"\bno\s+peanuts?\b|\bpeanut[-\s]?free\b", re.I), "peanuts"),
)

_STRIP_CLAUSES = (
    re.compile(r"\b(?:i(?:'m|\s+am)?|im)\s+lactose[-\s]?intolerant\b", re.I),
    re.compile(r"\blactose[-\s]?intolerant\b", re.I),
    re.compile(r"\bnot\s+(?:a\s+)?dairy\s+allerg(?:y|ies)\b", re.I),
    re.compile(r"\b(?:i(?:'m|\s+am)?|im)\s+gluten[-\s]?sensitive\b", re.I),
    re.compile(r"\bgluten[-\s]?sensitive\b", re.I),
    re.compile(r"\b(?:i(?:'m|\s+am)?|im)\s+(?:a\s+)?(?:vegan|vegetarian|jain|halal|kosher|gluten[-\s]?free)\b", re.I),
    re.compile(r"\bno\s+nuts?\b|\bnut[-\s]?free\b", re.I),
    re.compile(r"\bgluten[-\s]?free\b", re.I),
    re.compile(r"\bdairy[-\s]?free\b", re.I),
)


@dataclass
class RestrictionStatement:
    action: str = "none"  # apply | confirm | tighten | unsupported | none
    restriction_ids: list[str] = field(default_factory=list)
    tighten_ids: list[str] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    remove_allergens: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    scope: str = "self"  # self | other
    needs_confirm: bool = False
    confirm_message: str = ""
    dietary_preference: str | None = None
    remainder: str = ""


def parse_restriction_statement(query: str) -> RestrictionStatement:
    """Classify a restriction utterance. Confirm before relaxing medical rules."""
    q = query or ""
    stmt = RestrictionStatement(remainder=_strip_restriction_clauses(q))
    if _OTHER_SCOPE.search(q):
        stmt.scope = "other"
        stmt.action = "confirm"
        stmt.needs_confirm = True
        stmt.confirm_message = (
            "This looks like someone else's restriction. Confirm whose profile to use."
        )
        if _HAVE_ALLERGY.search(q) or "milk allergy" in q.lower() or "allergic" in q.lower():
            stmt.allergens = _split_list(_allergy_capture(q) or "milk")
        return stmt

    unsupported = [name for name, pat in _UNSUPPORTED if pat.search(q)]
    # "no seed oils" is supported as lifestyle; leave it out of unsupported.
    unsupported = [u for u in unsupported if u != "organic" or "organic" in q.lower()]
    if any(u in {"keto", "diabetic", "low_sodium", "low_fodmap"} for u in unsupported):
        keep = [u for u in unsupported if u in {"keto", "diabetic", "low_sodium", "low_fodmap", "organic"}]
        stmt.action = "unsupported"
        stmt.unsupported = keep
        stmt.confirm_message = (
            "I don't evaluate "
            + ", ".join(keep)
            + ". I can still check ingredients you paste against a diet or allergy profile."
        )
        return stmt

    if _USED_TO.search(q) or _GONE.search(q):
        stmt.action = "confirm"
        stmt.needs_confirm = True
        stmt.confirm_message = (
            "I will not remove a medical restriction without an explicit confirm."
        )
        return stmt

    if _TEMPORARY.search(q) and not _LACTOSE.search(q):
        stmt.action = "confirm"
        stmt.needs_confirm = True
        stmt.confirm_message = (
            "This sounds temporary. Confirm if I should change your saved profile."
        )
        _capture_fragments(q, stmt)
        stmt.tighten_ids = list(stmt.restriction_ids)
        return stmt

    if _LACTOSE.search(q):
        stmt.action = "tighten"
        stmt.needs_confirm = True
        stmt.restriction_ids = ["dairy_free"]
        stmt.tighten_ids = ["dairy_free"]
        stmt.dietary_preference = "Dairy-Free"
        stmt.confirm_message = (
            "I'll treat this as a dairy restriction for this check. "
            "Is lactose-free dairy acceptable, and should I save this on your profile?"
        )
        return stmt

    if _GLUTEN_SENSITIVE.search(q) and not (_CELIAC.search(q) and not _NOT_CELIAC.search(q)):
        stmt.action = "tighten"
        stmt.needs_confirm = True
        stmt.restriction_ids = ["gluten_free"]
        stmt.tighten_ids = ["gluten_free"]
        stmt.dietary_preference = "Gluten-Free"
        stmt.confirm_message = (
            "I'll treat this as gluten-free for this check. "
            "Is this a medical restriction (celiac) or a preference? "
            "I will not save it until you confirm."
        )
        return stmt

    not_diet = _NOT_DIET.search(q)
    if not_diet:
        stmt.action = "confirm"
        stmt.needs_confirm = True
        stmt.confirm_message = (
            "I will not remove a saved restriction without an explicit confirm."
        )
        return stmt

    please = _BARE_PLEASE.search(q)
    if please:
        diet = please.group(1).lower()
        stmt.action = "apply"
        stmt.restriction_ids = [_DIET_TO_RID.get(diet, diet)]
        stmt.dietary_preference = _DIET_DISPLAY.get(diet, diet.title())
        return stmt

    if _CELIAC.search(q) and not _NOT_CELIAC.search(q):
        stmt.action = "apply"
        stmt.restriction_ids = ["gluten_free"]
        stmt.dietary_preference = "Gluten-Free"
        return stmt

    allergic = _ALLERGIC.search(q) or _HAVE_ALLERGY.search(q)
    if allergic:
        stmt.action = "apply"
        stmt.allergens = _split_list(allergic.group(1))
        return stmt

    _capture_fragments(q, stmt)
    hits = len(stmt.restriction_ids) + len(stmt.allergens)
    leftover = (stmt.remainder or "").strip()
    # A single diet word on a food ("vegan cheese") is an ingredient, not a profile write.
    if hits >= 2 or (hits >= 1 and not leftover):
        stmt.action = "apply"
    else:
        stmt.restriction_ids = []
        stmt.allergens = []
        stmt.dietary_preference = None
    return stmt


def _capture_fragments(q: str, stmt: RestrictionStatement) -> None:
    for pat, rid, display in _FRAGMENT_DIETS:
        if pat.search(q) and rid not in stmt.restriction_ids:
            stmt.restriction_ids.append(rid)
            if stmt.dietary_preference is None:
                stmt.dietary_preference = display
    for pat, allergen in _FRAGMENT_ALLERGENS:
        if pat.search(q) and allergen not in stmt.allergens:
            stmt.allergens.append(allergen)


def _strip_restriction_clauses(q: str) -> str:
    out = q or ""
    for pat in _STRIP_CLAUSES:
        out = pat.sub(" ", out)
    out = re.sub(r"\s+", " ", out)
    out = re.sub(r"^\s*[,;.]+\s*", "", out)
    return out.strip(" ,;.")


def _allergy_capture(q: str) -> str | None:
    m = _ALLERGIC.search(q) or _HAVE_ALLERGY.search(q)
    return m.group(1) if m else None


def _split_list(raw: str) -> list[str]:
    parts = re.split(r"\s*(?:,|and|/)\s*", (raw or "").strip())
    out: list[str] = []
    for p in parts:
        p = p.strip().lower().rstrip(".")
        if p and p not in out:
            out.append(p)
    return out
