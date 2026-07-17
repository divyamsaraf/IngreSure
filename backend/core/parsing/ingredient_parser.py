"""
Preprocess complex ingredient strings into atomic ingredients for evaluation.
- Split by parentheses, brackets, braces and flatten nested lists.
- Normalize each part via normalizer.
- Detect <2% trace ingredients (informational unless they conflict with user profile).
"""
import re
import logging
from typing import List, Dict, Any, Optional, Callable

from core.normalization.normalizer import normalize_ingredient_key
from core.parsing.label_normalize import normalize_label_separators
from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text
from core.parsing.nesting_split import split_by_nesting

logger = logging.getLogger(__name__)

# Patterns for trace/minor ingredient labels (often at end of ingredient list)
TRACE_PATTERNS = [
    re.compile(r"less than 2%? of", re.IGNORECASE),
    re.compile(r"<2%?\s*of", re.IGNORECASE),
    re.compile(r"2%?\s*or less", re.IGNORECASE),
    re.compile(r"contains 2%?\s*or\s+less", re.IGNORECASE),
    re.compile(r"\(\s*<?\s*2\s*%?\s*\)", re.IGNORECASE),
    re.compile(r"\(&lt;2%\)", re.IGNORECASE),
    re.compile(r"\(\s*&lt;\s*2\s*%?\s*\)", re.IGNORECASE),
]

_LABEL_PREFIX = re.compile(
    r"^\s*(?:ingredients?|composition)\s*(?:[:;\-]\s*|\s+)",
    re.IGNORECASE,
)
_SUBSECTION_KEYWORDS = (
    "gravy",
    "sauce",
    "filling",
    "topping",
    "crust",
    "stuffing",
    "icing",
    "frosting",
    "batter",
    "coating",
    "marinade",
    "dressing",
    "glaze",
    "shell",
    "wrapper",
    "biscuit",
    "brownie",
    "cookie",
    "cake",
    "pie",
    "bar",
    "mix",
    "dough",
    "bread",
    "noodles",
    "pasta",
    "rice",
    "beans",
    "patty",
    "steak",
    "meat",
    "chicken",
    "pastry",
    "cream",
)
_SUBSECTION_KW_PATTERN = "|".join(re.escape(k) for k in _SUBSECTION_KEYWORDS)
_SUBSECTION_KW_HEADER = re.compile(
    rf"^\s*(?:{_SUBSECTION_KW_PATTERN})\s*:\s*",
    re.IGNORECASE,
)
_ALL_CAPS_PRODUCT_HEADER = re.compile(
    r"^\s*[A-Z][A-Z0-9\s/&'-]{2,}\s*:\s*",
)
_TITLE_CASE_SECTION_HEADER = re.compile(
    r"^\s*(?:[A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|&|and|or))+)\s*:\s*",
)
_INLINE_TRACE_PAREN = re.compile(r"\(\s*<?\s*2\s*%?\s*\)", re.IGNORECASE)
_SEMICOLON_CLAUSE = re.compile(
    r";\s+(?=contains\s+2%|<\s*2%|less\s+than\s+2%)",
    re.IGNORECASE,
)
_ALLERGEN_CONTAINS_COLON = re.compile(r"^\s*contains\s*:\s*", re.IGNORECASE)
_ALLERGEN_CONTAINS_BARE = re.compile(
    r"^\s*contains\s+(?!2\s*%|less\s+than|<\s*2)",
    re.IGNORECASE,
)
_EMBEDDED_SUBSECTION = re.compile(
    rf"\.\s+(?=(?:{_SUBSECTION_KW_PATTERN})\s*:\s*)",
    re.IGNORECASE,
)
_CATEGORY_CLAUSE = re.compile(
    r"\.\s+(?=(?:"
    r"vitamins?\s+and\s+minerals|minerals?\s+and\s+vitamins|"
    r"active\s+ingredient(?:s)?(?:\s+name)?|"
    r"other\s+ingredients?"
    r")\s*[:;\-]?\s*)",
    re.IGNORECASE,
)
_CATEGORY_HEADER = re.compile(
    r"^\s*(?:"
    r"vitamins?\s+and\s+minerals|minerals?\s+and\s+vitamins|"
    r"active\s+ingredient(?:s)?(?:\s+name)?|"
    r"other\s+ingredients?"
    r")\s*[:;\-]?\s*",
    re.IGNORECASE,
)
_TRACE_CLAUSE = re.compile(
    r"\.\s+(?=contains\s+2%|<\s*2%|less\s+than\s+2%)",
    re.IGNORECASE,
)
_CLAUSE_BREAK = re.compile(
    r"\.\s+(?=(?:"
    r"contains\s+2%|<\s*2%|less\s+than\s+2%|"
    r"may\s+(?:also\s+)?contain\b|"
    r"produced\s+in\s+a\s+facility\b|processed\s+in\s+a\s+facility\b|"
    r"made\s+in\s+a\s+facility\b|"
    r"vitamins?\s+and\s+minerals|minerals?\s+and\s+vitamins|"
    r"active\s+ingredient(?:s)?(?:\s+name)?|"
    r"other\s+ingredients?|"
    rf"{_SUBSECTION_KW_PATTERN}"
    r")\s*[:;\-]?\s*|"
    r"contains\s*:\s*|"
    r"contains\s+(?!2\s*%|less\s+than|<\s*2))",
    re.IGNORECASE,
)
MAY_CONTAIN_PATTERNS = [
    re.compile(r"may\s+(?:also\s+)?contain", re.IGNORECASE),
    re.compile(r"produced\s+in\s+a\s+facility", re.IGNORECASE),
    re.compile(r"processed\s+in\s+a\s+facility", re.IGNORECASE),
    re.compile(r"made\s+in\s+a\s+facility", re.IGNORECASE),
]
_TOP_LEVEL_SEP = re.compile(r"[,;](?![^(\[\{]*[\)\]\}])")
_QUALIFIERS = ("from", "derived from", "made from")
# Category headers before parenthetical lists (not standalone ingredients).
_STRUCTURAL_HEADERS = frozenset({
    "preservatives",
    "preservative",
    "colors",
    "colours",
    "color",
    "colour",
    "flavors",
    "flavours",
    "flavor",
    "flavour",
    "spices",
    "spice",
})


def _sanitize_atom_fragment(text: str) -> str:
    """Remove orphaned delimiters left by nesting splits (class B/C)."""
    t = (text or "").strip()
    if not t:
        return t
    t = re.sub(r"[\)\]\}]+\s*$", "", t)
    t = re.sub(r"^\s*[\(\[\{]+", "", t)
    return t.strip()


def _strip_category_headers(text: str) -> str:
    return _CATEGORY_HEADER.sub("", (text or "").strip())


def strip_label_boilerplate(text: str) -> str:
    t = (text or "").strip()
    while True:
        stripped = _LABEL_PREFIX.sub("", t).strip()
        if stripped == t:
            break
        t = stripped
    return t


def _strip_subsection_header(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return t
    t = _SUBSECTION_KW_HEADER.sub("", t)
    t = _ALL_CAPS_PRODUCT_HEADER.sub("", t)
    t = _TITLE_CASE_SECTION_HEADER.sub("", t)
    return t.strip()


def _strip_inline_trace_parens(text: str) -> str:
    return _INLINE_TRACE_PAREN.sub(" ", (text or "").strip()).strip()


def _strip_allergen_contains_markers(text: str) -> str:
    t = (text or "").strip()
    t = _ALLERGEN_CONTAINS_COLON.sub("", t)
    t = _ALLERGEN_CONTAINS_BARE.sub("", t)
    return t.strip()


def _is_allergen_contains_section(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _ALLERGEN_CONTAINS_COLON.search(t):
        return True
    return bool(_ALLERGEN_CONTAINS_BARE.search(t))


def _label_clauses(raw_str: str) -> List[str]:
    text = strip_label_boilerplate(raw_str)
    if not text:
        return []
    clauses: List[str] = []
    if _CLAUSE_BREAK.search(text):
        clauses = [c.strip() for c in _CLAUSE_BREAK.split(text) if c.strip()]
    elif _CATEGORY_CLAUSE.search(text):
        clauses = [c.strip() for c in _CATEGORY_CLAUSE.split(text) if c.strip()]
    elif _TRACE_CLAUSE.search(text):
        clauses = [c.strip() for c in _TRACE_CLAUSE.split(text) if c.strip()]
    else:
        clauses = [text]
    expanded: List[str] = []
    for clause in clauses:
        if _SEMICOLON_CLAUSE.search(clause):
            expanded.extend(c.strip() for c in _SEMICOLON_CLAUSE.split(clause) if c.strip())
        else:
            expanded.append(clause)
    return expanded


def _is_trace_clause(clause: str) -> bool:
    """True when a clause introduces <2% / minor-ingredient content (class D)."""
    body = _strip_subsection_header(_strip_category_headers(strip_label_boilerplate(clause)))
    if not body:
        return False
    return bool(
        re.match(
            r"^\s*(?:contains\s+2%|<\s*2%|less\s+than\s+2%)",
            body,
            re.IGNORECASE,
        )
    )


def _is_may_contain_section(text: str) -> bool:
    for pat in MAY_CONTAIN_PATTERNS:
        if pat.search(text):
            return True
    return False


def _strip_may_contain_markers(text: str) -> str:
    t = text
    t = re.sub(
        r"^\s*may\s+(?:also\s+)?contain(?:\s+traces?\s+of)?\s*[:;\-]?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"^\s*(?:produced|processed|made)\s+in\s+a\s+facility(?:\s+that)?\s*[:;\-]?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"^\s*(?:that\s+)?(?:also\s+)?(?:handles|processes|uses)\s+",
        "",
        t,
        flags=re.IGNORECASE,
    )
    return t.strip()


def _segment_canonical(part: str) -> str:
    """Collapse role/qualifier parentheticals before nesting split."""
    match = re.search(r"\(([^)]*)\)", part)
    if not match:
        return part
    inner = match.group(1).strip()
    if "," in inner:
        return part
    base = part[: match.start()].strip()
    inner_lower = inner.lower()
    if any(inner_lower.startswith(q) for q in _QUALIFIERS):
        return base
    if base and inner:
        return inner
    return part


def _segments_for_clause(clause: str) -> List[tuple[str, bool]]:
    segments: List[tuple[str, bool]] = []
    for chunk in _EMBEDDED_SUBSECTION.split(clause):
        chunk = chunk.strip()
        if not chunk:
            continue
        for seg in _TOP_LEVEL_SEP.split(chunk):
            seg = seg.strip()
            if not seg:
                continue
            seg = strip_label_boilerplate(seg)
            seg = _strip_subsection_header(seg)
            inline_trace = bool(_INLINE_TRACE_PAREN.search(seg))
            seg = _strip_inline_trace_parens(seg)
            collapsed = _segment_canonical(seg)
            if collapsed != seg:
                segments.append((collapsed, inline_trace))
            else:
                for piece in split_by_nesting(seg):
                    segments.append((piece, inline_trace))
    return segments


def _is_trace_section(text: str) -> bool:
    """Return True if this segment introduces trace/minor ingredients (<2%)."""
    for pat in TRACE_PATTERNS:
        if pat.search(text):
            return True
    return False


def _strip_trace_markers(text: str) -> str:
    """Remove '<2%' and similar markers from ingredient name for normalization."""
    t = text
    t = re.sub(r"\s*[<(]\s*&lt;\s*2\s*%?\s*[>)]\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*<\s*2\s*%?\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(
        r"\s*less\s+than\s+2%?\s*of\s*(?:each\s+of\s+)?(?:the\s+)?following\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*less\s+than\s+2%?\s*(?:of\s*)?:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*contains\s+2%?\s*or\s+less\s+of\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*less\s+than\s+2%?\s+of\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*<\s*2%?\s+of\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*contains\s+2%?\s*or\s+less\s*(?:of\s*)?(?:each\s+of\s+)?(?:the\s+)?following\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\s*contains\s+2%?\s*or\s+less\s*:?\s*",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\s*\(\s*<?\s*2\s*%?\s*\)\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*:+\s*", "", t)
    t = re.sub(r"^\s*less\s+of\s*:?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*of\s*(?:each\s+of\s+)?(?:the\s+)?following\s*:?\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


def preprocess_ingredients(
    raw_str: str,
    normalizer_fn: Optional[Callable[[str], str]] = None,
) -> List[Dict[str, Any]]:
    """
    Preprocess a raw ingredient label string into a list of atomic ingredients.

    Step 1: Strip label boilerplate and split trace clauses (e.g. after '.').
    Step 2: Split by comma/semicolon and flatten nesting delimiters.
    Step 3: Detect <2% trace segments; mark subsequent ingredients as trace.
    Step 4: Normalize each with normalizer_fn or normalize_ingredient_key.
    Step 5: Deduplicate by normalized key, preserving trace flag.
    """
    if not raw_str or not isinstance(raw_str, str):
        return []
    raw_str = normalize_label_separators(
        select_ingredient_label_text(fix_ocr_label_noise(raw_str))
    )
    norm_fn = normalizer_fn or normalize_ingredient_key

    result_by_key: Dict[str, Dict[str, Any]] = {}
    for clause in _label_clauses(raw_str):
        may_contain_until_end = _is_may_contain_section(clause) or _is_allergen_contains_section(clause)
        trace_until_end = _is_trace_clause(clause) and not may_contain_until_end
        clause_body = clause
        if may_contain_until_end:
            clause_body = _strip_may_contain_markers(clause_body)
            clause_body = _strip_allergen_contains_markers(clause_body)
        elif trace_until_end:
            clause_body = _strip_trace_markers(clause_body)
        clause_body = _strip_category_headers(clause_body)
        clause_body = _strip_subsection_header(clause_body)
        for part, segment_inline_trace in _segments_for_clause(clause_body):
            part_clean = part
            inline_trace = segment_inline_trace
            if not may_contain_until_end:
                part_clean = _strip_trace_markers(part_clean)
            part_clean = _strip_inline_trace_parens(part_clean)
            part_clean = _strip_category_headers(part_clean)
            part_clean = _sanitize_atom_fragment(part_clean)
            if not part_clean:
                continue
            is_trace = trace_until_end or _is_trace_section(part) or inline_trace
            is_may_contain = (
                may_contain_until_end
                or _is_may_contain_section(part)
                or _is_allergen_contains_section(part)
            )
            if _is_trace_section(part):
                trace_until_end = True
            if _is_may_contain_section(part) or _is_allergen_contains_section(part):
                may_contain_until_end = True
            key = norm_fn(part_clean)
            if not key or key in _STRUCTURAL_HEADERS:
                continue
            if key in result_by_key:
                result_by_key[key]["trace"] = result_by_key[key]["trace"] or is_trace
                result_by_key[key]["may_contain"] = (
                    result_by_key[key]["may_contain"] or is_may_contain
                )
            else:
                result_by_key[key] = {
                    "name": key,
                    "trace": is_trace,
                    "may_contain": is_may_contain,
                }

    return list(result_by_key.values())


def preprocess_ingredients_to_strings(
    raw_str: str,
    normalizer_fn: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Same as preprocess_ingredients but returns only the list of normalized name strings.
    Useful when trace handling is done at engine level via a separate trace set.
    """
    items = preprocess_ingredients(raw_str, normalizer_fn=normalizer_fn)
    return [x["name"] for x in items]
