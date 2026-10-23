"""
Preprocess complex ingredient strings into atomic ingredients for evaluation.
- Split by parentheses, brackets, braces and flatten nested lists.
- Normalize each part via normalizer.
- Detect <2% trace ingredients (informational unless they conflict with user profile).
"""
import logging
import os
import re
import time
from typing import List, Dict, Any, Optional, Callable

from core.normalization.normalizer import normalize_ingredient_key
from core.parsing.label_normalize import normalize_label_separators
from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text
from core.parsing.nesting_split import split_by_nesting, split_top_level
from core.parsing.bare_function_headers import parse_bare_function_headers
from core.parsing.parenthetical import (
    FUNCTION_HEADERS,
    additive_atom,
    classify_parenthetical,
)
from core.parsing.translation_pairs import expand_slash_atom

logger = logging.getLogger(__name__)

PARSE_BUDGET_S = float(os.environ.get("PARSE_BUDGET_S", "2"))


class ParseBudgetExceeded(Exception):
    """Parse exceeded PARSE_BUDGET_S; callers fail closed to UNCERTAIN."""

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
_ALLERGEN_CONTAINS_COLON = re.compile(
    r"^\s*(?:contains|contient|enthält)\s*[:;]\s*",
    re.IGNORECASE,
)
_ALLERGEN_CONTAINS_BARE = re.compile(
    r"^\s*(?:contains|contient|enthält)\s+(?!2\s*%|less\s+than|<\s*2)",
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
_QUALIFIERS = ("from", "derived from", "made from")
_PAREN_KEEP_OUTER = frozenset(
    {
        "purified",
        "filtered",
        "organic",
        "raw",
        "fresh",
        "unsweetened",
        "unsalted",
        "roasted",
        "cooked",
        "dried",
        "powdered",
        "ground",
        "minced",
        "chopped",
        "sliced",
        "color",
        "colour",
        "alkali",
    }
)
_FUNCTION_INNER = re.compile(
    r"^(?:to\s+|for\s+|as\s+)?"
    r"(?:preserve|preserv(?:e|ative)|color|colour|freshness|flavour|flavor|alkali)\b",
    re.IGNORECASE,
)
_ATTACHED_QUALIFIER = re.compile(
    r"\s+(?:"
    r"processed\s+with\s+alkali|"
    r"to\s+preserve\s+freshness|"
    r"color\s+added|"
    r"colour\s+added"
    r")\b",
    re.IGNORECASE,
)
_NATURAL_ARTIFICIAL = re.compile(
    r"\bnatural\s+and\s+artificial\s+(?=flavou?rs?\b)",
    re.IGNORECASE,
)
_BARE_QUALIFIER_ATOMS = frozenset({
    "color",
    "colour",
    "alkali",
    "natural",
    "artificial",
    "freshness",
    "added",
    "color added",
    "colour added",
    "i",
    "ii",
    "iii",
    "iv",
})
_SECTION_SLASH = re.compile(
    r"\s*/\s*(?=(?:contains|contient|enthält|gluten\s+source|source\s+de\s+gluten)\s*:)",
    re.IGNORECASE,
)
# Category headers before parenthetical lists (not standalone ingredients).
_STRUCTURAL_HEADERS = frozenset(FUNCTION_HEADERS) | frozenset({
    "spices",
    "spice",
})


def _sanitize_atom_fragment(text: str) -> str:
    """Remove orphaned delimiters left by nesting splits (class B/C)."""
    t = (text or "").strip()
    if not t:
        return t
    stripped = re.sub(r"[\)\]\}]+\s*$", "", t)
    # Keep the closing delimiter when it belongs to an additive sub-variant
    # (INS 322(ii), E471(a)) rather than an orphan from nesting split.
    if stripped.count("(") > stripped.count(")") or stripped.count("[") > stripped.count("]"):
        pass
    else:
        t = stripped
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
    if _SECTION_SLASH.search(text):
        out: List[str] = []
        for chunk in _SECTION_SLASH.split(text):
            out.extend(_label_clauses(chunk))
        return out
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


# Pure quantity: "49.5%", "49,5 %", "min. 62%", "max 10%", "approx. 5%", "~5%"
_COMPOSITION_PERCENT = re.compile(
    r"^(?:(?:min|max|minimum|maximum|approx|approximately|about|ca|avg|average)\.?\s+)?"
    r"~?\s*\d+(?:[.,]\d+)?\s*%$",
    re.IGNORECASE,
)
_COMPOSITION_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?$")
_ADDITIVE_HEAD = re.compile(r"^(?:e|ins)\s*\d{2,4}$", re.IGNORECASE)
_ADDITIVE_SUBVARIANT = re.compile(r"^(?:[ivxlcdm]+|[a-z])$", re.IGNORECASE)
_BARE_INS_SUB = re.compile(r"^(?:[ivxlcdm]{2,}|[a-z])$", re.IGNORECASE)


def _glue_ins_subvariants(pieces: List[str]) -> List[str]:
    """Attach a leftover roman/letter fragment onto the preceding additive number."""
    out: List[str] = []
    for piece in pieces:
        t = (piece or "").strip()
        if not t:
            continue
        if out and _BARE_INS_SUB.match(t) and re.search(r"\d{2,4}\s*$", out[-1]):
            out[-1] = additive_atom(f"{out[-1]}({t})")
            continue
        out.append(t)
    return out


def _segment_canonical(part: str) -> str:
    """Collapse role/qualifier parentheticals before nesting split.

    Composition percents like ``PEANUTS (49.5%)`` or ``wheat flour (min. 62%)``
    keep the ingredient name; only synonym/role parentheticals
    (e.g. ``Vitamin C (ascorbic acid)``) collapse to the inner form.
    """
    match = re.search(r"\(([^)]*)\)", part)
    if not match:
        return part
    inner = match.group(1).strip()
    if "," in inner:
        return part
    base = part[: match.start()].strip()
    # Composition % is not a synonym — leave segment intact for nesting split
    # + quantity strip (must not collapse to "49.5%" / "min" or drop hazards).
    if _COMPOSITION_PERCENT.match(inner) or _COMPOSITION_NUMBER.match(inner):
        return part
    if _ADDITIVE_HEAD.match(base) and _ADDITIVE_SUBVARIANT.match(inner):
        return part
    inner_lower = inner.lower()
    if (
        inner_lower in _PAREN_KEEP_OUTER
        or any(inner_lower.startswith(q) for q in _QUALIFIERS)
        or _FUNCTION_INNER.match(inner_lower)
    ):
        return base
    if base and inner:
        # Synonym collapse (e.g. Vitamin C (ascorbic acid)) must not erase a
        # hazard surface form on the outer token (Wheat Flour (Maida),
        # Peanut Butter (Unsweetened)).
        try:
            from core.parsing.hazard_lexicon import hazard_hits_in_text
        except Exception:  # pragma: no cover
            hazard_hits_in_text = lambda _t: set()  # type: ignore
        if hazard_hits_in_text(base) - hazard_hits_in_text(inner):
            return part
        return inner
    return part


_BARE_ADDITIVE_CODE = re.compile(
    r"^(?:e|ins)?\s*\d{2,4}(?:[a-z]|\([ivxlcdm]+\)|\([a-z]\))?$",
    re.IGNORECASE,
)


def _bare_function_atoms(
    seg: str, pending_class: str | None
) -> tuple[list[str] | None, str | None]:
    """Expand bracket-less AU/NZ headers; carry INS lists across commas."""
    hits = parse_bare_function_headers(seg)
    if hits:
        atoms: list[str] = []
        pending = pending_class
        for hit in hits:
            if hit.substance:
                atoms.append(hit.substance)
                pending = None
            elif hit.code:
                atoms.append(additive_atom(hit.code))
                pending = hit.function_class
        if atoms:
            return atoms, pending
        return None, None
    if pending_class and _BARE_ADDITIVE_CODE.match((seg or "").strip()):
        return [additive_atom(seg.strip())], pending_class
    return None, None


def _segments_for_clause(clause: str) -> List[tuple[str, bool]]:
    segments: List[tuple[str, bool]] = []
    for chunk in _EMBEDDED_SUBSECTION.split(clause):
        chunk = chunk.strip()
        if not chunk:
            continue
        pending_fn: str | None = None
        for seg in split_top_level(chunk):
            seg = seg.strip()
            if not seg:
                continue
            seg = strip_label_boilerplate(seg)
            seg = _strip_subsection_header(seg)
            inline_trace = bool(_INLINE_TRACE_PAREN.search(seg))
            seg = _strip_inline_trace_parens(seg)
            kind, payload = classify_parenthetical(seg)
            if kind == "none":
                expanded, pending_fn = _bare_function_atoms(seg, pending_fn)
                if expanded is not None:
                    for atom in expanded:
                        segments.append((atom, inline_trace))
                    continue
                pending_fn = None
            else:
                pending_fn = None
            if kind in ("function_header_numbers", "ins_e_list"):
                for code in payload.get("codes") or []:
                    segments.append((additive_atom(code), inline_trace))
                continue
            if kind == "function_header_payload":
                for inner_item in payload.get("inners") or [payload.get("inner") or ""]:
                    item = (inner_item or "").strip()
                    if item:
                        segments.append((item, inline_trace))
                continue
            if kind == "additive_subvariant":
                code = payload.get("codes") or [
                    f"{payload.get('base', '')}({payload.get('inner', '')})"
                ]
                segments.append((additive_atom(code[0]), inline_trace))
                continue
            if kind in ("name_function", "quantity", "claim", "translation"):
                base = (payload.get("base") or "").strip()
                if base:
                    segments.append((base, inline_trace))
                continue
            if kind == "name_origin":
                base = (payload.get("base") or "").strip()
                inner = (payload.get("inner") or "").strip()
                if inner:
                    segments.append((inner, inline_trace))
                # Short origin token (soya, milk): keep the outer name too.
                # Multi-word inners are the real ingredient (Sourdough (Wheat Flour)).
                if base and len(inner.split()) <= 1:
                    segments.append((base, inline_trace))
                continue
            collapsed = _segment_canonical(seg)
            if collapsed != seg:
                segments.append((collapsed, inline_trace))
            else:
                pieces = list(split_by_nesting(seg))
                # Nesting split turns "Preservatives (A, B)" into
                # ["Preservatives", "A", "B"]. The category word is only a
                # header when children were expanded — drop it so the umbrella
                # does not double-count beside its listed constituents.
                if len(pieces) > 1:
                    head = normalize_ingredient_key(pieces[0])
                    if head in _STRUCTURAL_HEADERS:
                        pieces = pieces[1:]
                glued = _glue_ins_subvariants(pieces)
                for piece in glued:
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
    t0 = time.monotonic()
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
            part_clean = _NATURAL_ARTIFICIAL.sub("", part_clean)
            part_clean = _ATTACHED_QUALIFIER.sub("", part_clean).strip()
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
            for slash_part in expand_slash_atom(part_clean):
                _record_atom(
                    result_by_key,
                    slash_part,
                    part,
                    is_trace=is_trace,
                    is_may_contain=is_may_contain,
                    norm_fn=norm_fn,
                )

    if PARSE_BUDGET_S >= 0 and (time.monotonic() - t0) > PARSE_BUDGET_S:
        raise ParseBudgetExceeded(
            f"ingredient parse exceeded {PARSE_BUDGET_S}s"
        )
    return list(result_by_key.values())


def _record_atom(
    result_by_key: Dict[str, Dict[str, Any]],
    part_clean: str,
    part: str,
    *,
    is_trace: bool,
    is_may_contain: bool,
    norm_fn: Callable[[str], str],
) -> None:
    key = norm_fn(part_clean)
    if not key or key in _BARE_QUALIFIER_ATOMS:
        return
    # Structural category words (spices, flavors, preservatives) are
    # headers when they introduce a parenthetical list. A bare token
    # the user typed ("Are spices safe?") is a real ingredient and
    # must NOT be dropped — otherwise compound umbrellas vanish and
    # falsely land in Safe.
    if key in _STRUCTURAL_HEADERS and (
        "(" in part or "[" in part or "{" in part or ":" in part
    ):
        return
    if key in result_by_key:
        result_by_key[key]["trace"] = result_by_key[key]["trace"] or is_trace
        result_by_key[key]["may_contain"] = (
            result_by_key[key]["may_contain"] or is_may_contain
        )
        return
    result_by_key[key] = {
        "name": key,
        "trace": is_trace,
        "may_contain": is_may_contain,
    }


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
