"""
Rule-based intent detector for conversational grocery safety queries.
Detects: PROFILE_UPDATE, INGREDIENT_QUERY, MIXED, GREETING, GENERAL_QUESTION
No LLM dependency – fully deterministic pattern matching.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Diet keywords → canonical display names (sorted longest-first for matching)
# ---------------------------------------------------------------------------
DIET_KEYWORDS: Dict[str, str] = {
    "hindu non vegetarian": "Hindu Non Vegetarian",
    "hindu non veg": "Hindu Non Vegetarian",
    "hindu nonveg": "Hindu Non Vegetarian",
    "hindu vegetarian": "Hindu Veg",
    "lacto vegetarian": "Lacto Vegetarian",
    "lacto-vegetarian": "Lacto Vegetarian",
    "ovo vegetarian": "Ovo Vegetarian",
    "ovo-vegetarian": "Ovo Vegetarian",
    "hindu veg": "Hindu Veg",
    "pescatarian": "Pescatarian",
    "gluten free": "Gluten-Free",
    "gluten-free": "Gluten-Free",
    "dairy free": "Dairy-Free",
    "dairy-free": "Dairy-Free",
    "vegetarian": "Vegetarian",
    "egg free": "Egg-Free",
    "egg-free": "Egg-Free",
    "vegan": "Vegan",
    "halal": "Halal",
    "kosher": "Kosher",
    "jain": "Jain",
    "hindu": "Hindu Veg",
}

_DIET_PATTERN_KEYS = sorted(DIET_KEYWORDS.keys(), key=len, reverse=True)
_DIET_REGEX = "|".join(re.escape(k) for k in _DIET_PATTERN_KEYS)

# Profile-update sentence patterns (captures the diet keyword)
_PROFILE_PATTERNS = [
    re.compile(rf"\b(?:i\s+am|i'm|im)\s+(?:a\s+)?({_DIET_REGEX})\b", re.IGNORECASE),
    re.compile(rf"\b(?:i\s+follow|i\s+eat|my\s+diet\s+is)\s+(?:a\s+|the\s+)?({_DIET_REGEX})\s*(?:diet|lifestyle)?\b", re.IGNORECASE),
    re.compile(rf"\bi(?:'m| am)\s+on\s+(?:a\s+)?({_DIET_REGEX})\s*(?:diet)?\b", re.IGNORECASE),
    re.compile(rf"\b(?:my\s+religion\s+is|i\s+practice)\s+({_DIET_REGEX})\b", re.IGNORECASE),
    re.compile(rf"\b(?:i\s+eat)\s+({_DIET_REGEX})\b", re.IGNORECASE),
    re.compile(rf"\bswitch(?:ing)?\s+(?:to|my\s+diet\s+to)\s+({_DIET_REGEX})\b", re.IGNORECASE),
]

# Allergen-update sentence patterns
_ALLERGEN_PATTERNS = [
    re.compile(r"\b(?:i'm|i\s+am|i'm)\s+allergic\s+to\s+(.+?)(?:\.|,\s*(?:can|is|and)|$)", re.IGNORECASE),
    re.compile(r"\b(?:i\s+have)\s+(?:a\s+)?(.+?)\s+allergy\b", re.IGNORECASE),
    re.compile(r"\b(?:my\s+allerg(?:ies|y|ens?)\s+(?:are|is))\s+(.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"\b(?:add|set)\s+(?:my\s+)?allerg(?:ens?|ies?)\s+(?:to\s+)?(.+?)(?:\.|$)", re.IGNORECASE),
]

# Allergen-removal patterns
_ALLERGEN_REMOVE_PATTERNS = [
    re.compile(r"\b(?:remove|delete|drop|clear)\s+(.+?)\s+(?:from\s+)?(?:my\s+)?allerg(?:ens?|ies?)[\?\.\!]?\s*$", re.IGNORECASE),
    re.compile(r"\b(?:i'm\s+not|i\s+am\s+not|i'm\s+no\s+longer)\s+allergic\s+to\s+(.+?)[\?\.\!]?\s*$", re.IGNORECASE),
]

# Lifestyle-update patterns
_LIFESTYLE_PATTERNS = [
    re.compile(r"\b(?:i\s+don't|i\s+do\s+not|i\s+can't|no)\s+(?:eat|drink|consume|have)\s+(alcohol|onion|garlic|onions|garlics?)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+avoid|no)\s+(alcohol|onion|garlic|palm\s+oil|onions|garlics?|seed\s+oils?|gmos?|artificial\s+colors?)\b", re.IGNORECASE),
    re.compile(r"\b(?:set|add|update)\s+(?:my\s+)?lifestyle\s+(?:to\s+)?(.+?)[\?\.\!]?\s*$", re.IGNORECASE),
]

# Lifestyle keyword → canonical lifestyle flag
_LIFESTYLE_MAP = {
    "alcohol": "no alcohol",
    "onion": "no onion",
    "onions": "no onion",
    "garlic": "no garlic",
    "garlics": "no garlic",
    "palm oil": "no palm oil",
    "seed oil": "no seed oils",
    "seed oils": "no seed oils",
    "gmo": "no gmos",
    "gmos": "no gmos",
    "artificial color": "no artificial colors",
    "artificial colors": "no artificial colors",
}

# ---------------------------------------------------------------------------
# Third-person / indirect diet+ingredient queries
# These extract BOTH a diet AND ingredient(s) in one go
# ---------------------------------------------------------------------------
# Plural-tolerant diet regex: "vegans" → "vegan", "jains" → "jain"
_DIET_REGEX_PLURAL = rf"(?:{_DIET_REGEX})(?:s|'s)?"

_THIRD_PERSON_PATTERNS = [
    # "can jain eat onion?" / "can vegans eat honey?" / "can a halal person eat pork?"
    re.compile(
        rf"\bcan\s+(?:a\s+)?({_DIET_REGEX_PLURAL})(?:\s+(?:people|person|persons))?\s+(?:eat|have|consume|use)\s+(.+?)[\?\.\!]?\s*$",
        re.IGNORECASE,
    ),
    # "does jain allow onion?" / "does vegan allow honey?"
    re.compile(
        rf"\b(?:does|do)\s+(?:a\s+|the\s+)?({_DIET_REGEX_PLURAL})(?:\s+(?:diet|people|person))?\s+(?:allow|permit|include|restrict|forbid|ban)\s+(.+?)[\?\.\!]?\s*$",
        re.IGNORECASE,
    ),
    # "is onion jain?" / "is pork halal?" / "is gelatin kosher?" / "are eggs vegan?"
    re.compile(
        rf"\b(?:is|are)\s+(.+?)\s+({_DIET_REGEX_PLURAL})(?:\s+(?:safe|friendly|compatible|compliant|approved))?[\?\.\!]?\s*$",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# Ingredient-query patterns (capture the ingredient portion)
# ---------------------------------------------------------------------------
_INGREDIENT_QUERY_PATTERNS = [
    # "can I eat eggs?" / "can I have cheese and milk?"
    re.compile(r"\bcan\s+i\s+(?:eat|have|consume|take|use)\s+(.+?)[\?\.\!]?\s*$", re.IGNORECASE),
    # "is eggs safe?" / "are eggs safe?" / "is cheese ok?" / "is bread allowed?"
    re.compile(
        r"\b(?:is|are)\s+(.+?)\s+(?:safe|ok|okay|allowed|permitted|suitable|fine|good|acceptable|compatible)"
        r"(?:\s+(?:for\s+me|for\s+my\s+diet|to\s+eat))?[\?\.\!]?\s*$",
        re.IGNORECASE,
    ),
    # "eggs safe?" / "cheese ok?"
    re.compile(r"^(.+?)\s+(?:safe|ok|okay|allowed|permitted|suitable|fine|good)[\?\.\!]?\s*$", re.IGNORECASE),
    # "what about eggs?" / "how about cheese?"
    re.compile(r"\b(?:what|how)\s+about\s+(.+?)[\?\.\!]?\s*$", re.IGNORECASE),
    # "check eggs" / "analyze cheese"
    re.compile(r"^\s*(?:check|analyze|evaluate|test|verify)\s+(.+?)[\?\.\!]?\s*$", re.IGNORECASE),
    # "Ingredients: X, Y, Z" (explicit label)
    re.compile(r"\b(?:ingredients?)\s*[:;]\s*(.+)", re.IGNORECASE),
]

# Greeting patterns — matches single-word and multi-part greetings
_GREETING_RE = re.compile(
    r"^\s*(?:hi|hello|hey|howdy|good\s+(?:morning|afternoon|evening)|greetings|what'?s?\s+up|yo)"
    r"(?:\s*[,!.]?\s*(?:how\s+(?:are\s+you|is\s+it\s+going|do\s+you\s+do|are\s+things)"
    r"|how'?s?\s+(?:it\s+going|everything|life)|nice\s+to\s+meet\s+you"
    r"|there|everyone|all))?"
    r"\s*[\?\.\!]?\s*$",
    re.IGNORECASE,
)

# Purely conversational phrases (not greetings, not ingredients, not questions)
_CONVERSATIONAL_RE = re.compile(
    r"^\s*(?:how\s+are\s+you|how'?s?\s+it\s+going|how\s+do\s+you\s+do"
    r"|thank\s*(?:s| you)|thanks?\s+a\s+lot|much\s+appreciated"
    r"|ok(?:ay)?|cool|nice|great|awesome|got\s+it|understood"
    r"|bye|goodbye|see\s+you|take\s+care|good\s+night"
    r"|yes|no|nope|yep|yeah|sure|nah"
    r"|what\s+can\s+you\s+do|who\s+are\s+you|what\s+are\s+you)"
    r"\s*[\?\.\!]?\s*$",
    re.IGNORECASE,
)

# General-question patterns
_GENERAL_QUESTION_RES = [
    re.compile(r"\bwhat\s+is\s+", re.IGNORECASE),
    re.compile(r"\btell\s+me\s+about\s+", re.IGNORECASE),
    re.compile(r"\bwhere\s+does\s+.+?\s+come\s+from\b", re.IGNORECASE),
    re.compile(r"\bhow\s+(?:is|are)\s+.+?\s+made\b", re.IGNORECASE),
    re.compile(r"\bexplain\b", re.IGNORECASE),
    re.compile(r"\b(?:suggest|recommend|brainstorm|alternative|substitute|replace|instead|option|recipe)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Data class for parsed result
# ---------------------------------------------------------------------------
@dataclass
class ParsedIntent:
    """Result of intent detection."""
    intent: str  # PROFILE_UPDATE | INGREDIENT_QUERY | MIXED | GREETING | GENERAL_QUESTION
    profile_updates: Dict[str, object] = field(default_factory=dict)
    ingredients: List[str] = field(default_factory=list)
    original_query: str = ""

    @property
    def has_profile_update(self) -> bool:
        return bool(self.profile_updates)

    @property
    def has_ingredients(self) -> bool:
        return bool(self.ingredients)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _extract_diet(query: str) -> Tuple[Optional[str], str]:
    """Return (canonical_diet_name, remaining_query) or (None, query)."""
    for pat in _PROFILE_PATTERNS:
        m = pat.search(query)
        if m:
            matched = m.group(1).lower().strip()
            canonical = DIET_KEYWORDS.get(matched)
            if canonical:
                remaining = (query[: m.start()] + " " + query[m.end() :]).strip()
                remaining = re.sub(r"^\s*[,;.]+\s*", "", remaining).strip()
                remaining = re.sub(r"\s+", " ", remaining)
                return canonical, remaining
    return None, query


def _extract_allergens(query: str) -> Tuple[List[str], str]:
    """Return ([allergen_names], remaining_query)."""
    allergens: List[str] = []
    remaining = query
    for pat in _ALLERGEN_PATTERNS:
        m = pat.search(remaining)
        if m:
            raw = m.group(1).strip()
            for a in re.split(r"\s*(?:,|and)\s*", raw):
                a = a.strip().lower()
                if a:
                    allergens.append(a)
            remaining = (remaining[: m.start()] + " " + remaining[m.end() :]).strip()
            remaining = re.sub(r"\s+", " ", remaining)
    return allergens, remaining


def _extract_allergen_removals(query: str) -> Tuple[List[str], str]:
    """Return ([allergens_to_remove], remaining_query)."""
    removals: List[str] = []
    remaining = query
    for pat in _ALLERGEN_REMOVE_PATTERNS:
        m = pat.search(remaining)
        if m:
            raw = m.group(1).strip()
            for a in re.split(r"\s*(?:,|and)\s*", raw):
                a = a.strip().lower()
                if a:
                    removals.append(a)
            remaining = (remaining[: m.start()] + " " + remaining[m.end() :]).strip()
            remaining = re.sub(r"\s+", " ", remaining)
    return removals, remaining


def _extract_lifestyle(query: str) -> Tuple[List[str], str]:
    """Return ([lifestyle_flags], remaining_query)."""
    flags: List[str] = []
    remaining = query
    for pat in _LIFESTYLE_PATTERNS:
        m = pat.search(remaining)
        if m:
            keyword = m.group(1).strip().lower()
            flag = _LIFESTYLE_MAP.get(keyword, f"no {keyword}")
            if flag and flag not in flags:
                flags.append(flag)
            remaining = (remaining[: m.start()] + " " + remaining[m.end() :]).strip()
            remaining = re.sub(r"\s+", " ", remaining)
    return flags, remaining


def _extract_ingredients_from_text(text: str) -> List[str]:
    """Extract ingredient names from conversational text."""
    text = text.strip()
    if not text:
        return []
    for pat in _INGREDIENT_QUERY_PATTERNS:
        m = pat.search(text)
        if m:
            return _split_ingredients(m.group(1).strip())
    # Fallback: if the text looks like a plain ingredient list (no verbs)
    cleaned = _clean_for_ingredients(text)
    if cleaned:
        return _split_ingredients(cleaned)
    return []


# Product/container words — keep compound "X with Y" intact when X is a product
_PRODUCT_CONTAINER_WORDS = {
    "burger", "burgers", "bar", "bars", "protein bar", "protin bar", "energy bar",
    "cake", "cakes", "sandwich", "sandwiches", "wrap", "wraps",
    "pizza", "pizzas", "pie", "pies",
    "cookie", "cookies", "biscuit", "biscuits", "cracker", "crackers",
    "chip", "chips", "crisp", "crisps",
    "noodle", "noodles", "pasta", "ramen",
    "soup", "soups", "salad", "salads", "stew", "curry",
    "juice", "drink", "smoothie", "shake", "milkshake",
    "cereal", "granola", "muesli",
    "muffin", "muffins", "bagel", "pancake", "waffle", "toast", "roll", "bun",
    "doughnut", "donut", "pastry", "croissant",
    "ice cream", "gelato", "sorbet", "pudding", "custard",
    "candy", "chocolate bar", "snack", "snacks",
    "sausage", "hotdog", "hot dog", "kebab", "taco", "tacos",
    "bread", "roti", "naan", "paratha", "chapati",
}


def _split_ingredients(text: str) -> List[str]:
    """Split ingredient text into a deduplicated list.

    Preserves compound items like 'burger with chicken' when the left side
    is a known product/container word.  Otherwise splits on 'with' as a
    conjunction (e.g. 'bread and eggs').
    """
    t = re.sub(r"[?\!]+", "", text).strip()
    # Replace "and" / "or" with comma (but NOT "with" — handled per-chunk)
    t = re.sub(r"\s+(?:and|&)\s+", ", ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+or\s+", ", ", t, flags=re.IGNORECASE)
    stopwords = {"the", "a", "an", "some", "any", "this", "that", "it", "for", "me", "my", "in", "on", "to"}
    result: List[str] = []
    seen: set = set()

    for chunk in t.split(","):
        chunk = chunk.strip().rstrip(".")
        if not chunk or len(chunk) < 2:
            continue
        words = chunk.lower().split()
        if all(w in stopwords for w in words):
            continue

        # Check for "X with Y" compound
        with_match = re.match(r"^(.+?)\s+with\s+(.+)$", chunk, re.IGNORECASE)
        if with_match:
            left = with_match.group(1).strip()
            right = with_match.group(2).strip()
            if left.lower() in _PRODUCT_CONTAINER_WORDS:
                # Keep as compound: "burger with chicken"
                key = chunk.lower().strip()
                if key not in seen:
                    seen.add(key)
                    result.append(chunk)
            else:
                # Split: treat "with" as conjunction
                for part in [left, right]:
                    key = part.lower().strip()
                    if key not in seen and len(part) >= 2:
                        pw = part.lower().split()
                        if not all(w in stopwords for w in pw):
                            seen.add(key)
                            result.append(part)
        else:
            key = chunk.lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(chunk)
    return result


def _clean_for_ingredients(text: str) -> str:
    """Strip conversational fluff; return empty string if nothing ingredient-like remains."""
    t = text.strip()
    t = re.sub(r"^(?:hi|hello|hey|please|kindly)\s*,?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:please|kindly|could\s+you|would\s+you|can\s+you)\s+(?:check|tell\s+me|let\s+me\s+know)\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bfor\s+(?:me|my\s+\w+)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\?+\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Reject conversational phrases and request for help
    if re.search(r"\b(?:think|know|explain|describe|tell|help|find|suggest|recommend|brainstorm|alternative|substitute|replace|instead|option|recipe)\b", t, re.IGNORECASE):
        return ""
    # Reject greetings / conversational noise that survived stripping
    if re.match(
        r"^(?:how\s+are\s+you|how'?s?\s+it\s+going|how\s+do\s+you\s+do|thank|thanks|bye|goodbye|ok|okay"
        r"|cool|nice|great|awesome|yes|no|yep|yeah|sure|nah)\b",
        t, re.IGNORECASE,
    ):
        return ""
    return t


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def detect_intent(query: str) -> ParsedIntent:
    """
    Parse a natural language query into structured intent.

    Examples:
        "I am Jain can I eat eggs?"
            → MIXED  profile_updates={"dietary_preference": "Jain"}  ingredients=["eggs"]
        "Is cheese okay?"
            → INGREDIENT_QUERY  ingredients=["cheese"]
        "I follow a vegan diet"
            → PROFILE_UPDATE  profile_updates={"dietary_preference": "Vegan"}
        "Hello"
            → GREETING
        "eggs, milk, flour"
            → INGREDIENT_QUERY  ingredients=["eggs", "milk", "flour"]
    """
    query = (query or "").strip()
    if not query:
        return ParsedIntent(intent="GENERAL_QUESTION", original_query=query)

    # /update command → delegate to existing handler (intent = PROFILE_UPDATE)
    if query.lstrip().lower().startswith("/update"):
        return ParsedIntent(intent="PROFILE_UPDATE", original_query=query)

    # Greeting (single-word and multi-part like "hi, how are you?")
    if _GREETING_RE.match(query):
        return ParsedIntent(intent="GREETING", original_query=query)

    # Conversational phrase (not an ingredient query)
    if _CONVERSATIONAL_RE.match(query):
        return ParsedIntent(intent="GREETING", original_query=query)

    # ---- Third-person / indirect diet+ingredient queries ----
    # "can jain eat onion?", "is pork halal?", "does vegan allow honey?"
    for pat in _THIRD_PERSON_PATTERNS:
        m = pat.search(query)
        if m:
            groups = m.groups()
            # Pattern 3 ("is X diet?") has ingredient first, diet second
            if pat.pattern.startswith(r"\b(?:is|are)"):
                ingredient_raw, diet_raw = groups[0], groups[1]
            else:
                diet_raw, ingredient_raw = groups[0], groups[1]
            diet_key = diet_raw.lower().strip()
            # Strip trailing 's or s (plural tolerance: vegans→vegan)
            canonical_diet = DIET_KEYWORDS.get(diet_key)
            if not canonical_diet and diet_key.endswith("'s"):
                canonical_diet = DIET_KEYWORDS.get(diet_key[:-2])
            if not canonical_diet and diet_key.endswith("s"):
                canonical_diet = DIET_KEYWORDS.get(diet_key[:-1])
            if canonical_diet:
                ings = _split_ingredients(ingredient_raw.strip())
                if ings:
                    return ParsedIntent(
                        intent="MIXED",
                        profile_updates={"dietary_preference": canonical_diet},
                        ingredients=ings,
                        original_query=query,
                    )

    # ---- Extract profile signals ----
    profile_updates: Dict[str, object] = {}

    diet_name, remaining = _extract_diet(query)
    if diet_name:
        profile_updates["dietary_preference"] = diet_name

    allergens, remaining = _extract_allergens(remaining)
    if allergens:
        profile_updates["allergens"] = allergens

    allergen_removals, remaining = _extract_allergen_removals(remaining)
    if allergen_removals:
        profile_updates["remove_allergens"] = allergen_removals

    lifestyle_flags, remaining = _extract_lifestyle(remaining)
    if lifestyle_flags:
        profile_updates["lifestyle"] = lifestyle_flags

    # ---- Check general-question patterns BEFORE ingredient extraction ----
    is_general = any(p.search(query) for p in _GENERAL_QUESTION_RES)

    # ---- Extract ingredients ----
    ingredients: List[str] = []
    if not is_general:
        ingredients = _extract_ingredients_from_text(remaining)
        # Only fall back to original query if profile extraction didn't already succeed
        # (avoids "I am Jain" → "jain" extracted as ingredient)
        if not ingredients and remaining != query and not profile_updates:
            ingredients = _extract_ingredients_from_text(query)

    # Filter out diet names that leaked into ingredients
    if ingredients:
        diet_names_lower = {k for k in DIET_KEYWORDS}
        ingredients = [i for i in ingredients if i.lower().strip() not in diet_names_lower]

    # ---- Classify intent ----
    has_profile = bool(profile_updates)
    has_ingredients = bool(ingredients)

    if has_profile and has_ingredients:
        intent = "MIXED"
    elif has_profile:
        intent = "PROFILE_UPDATE"
    elif has_ingredients:
        intent = "INGREDIENT_QUERY"
    elif is_general:
        intent = "GENERAL_QUESTION"
    else:
        # Last-resort: treat the whole query as potential ingredient text
        fallback = _extract_ingredients_from_text(query)
        # Filter diet names again
        if fallback:
            diet_names_lower = {k for k in DIET_KEYWORDS}
            fallback = [i for i in fallback if i.lower().strip() not in diet_names_lower]
        if fallback:
            return ParsedIntent(intent="INGREDIENT_QUERY", ingredients=fallback, original_query=query)
        intent = "GENERAL_QUESTION"

    return ParsedIntent(
        intent=intent,
        profile_updates=profile_updates,
        ingredients=ingredients,
        original_query=query,
    )
