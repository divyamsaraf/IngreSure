"""Safe commodity-head + allowlisted facet reduction (design §9.3.1).

USDA / staging rows often look like ``Broccoli, raw``. Users type ``broccoli``.
``normalize_ingredient_key`` strips commas (``broccoli raw``), so this module
handles both punctuated dump labels and already-normalized keys.

L3 facet strip: closed allowlists only. Callers must verify the residual
already resolves (never invent a parent). Never strip juice/puree/butter/
chestnut generically. Never first-token parent (``cabbage bok choy``).
"""
from __future__ import annotations

import re
from typing import Iterable

from core.normalization.normalizer import normalize_ingredient_key

_PREP = (
    r"raw|dried|dry|fresh|frozen|unprepared|canned|smoked|cooked|"
    r"ground|pure|shelled|distilled|whole|mixed"
)

# Exactly one comma, then a prep token — safe to expose the left side as a chat key.
_SIMPLE_PREP_COMMA = re.compile(
    rf"^([^,]+),\s*({_PREP})\s*$",
    re.IGNORECASE,
)

# After key-normalize strips commas: ``broccoli raw``.
_SIMPLE_PREP_SPACE = re.compile(
    rf"^(.+?)\s+({_PREP})$",
    re.IGNORECASE,
)

_SPICES_COMMA = re.compile(r"^spices,\s*(.+)$", re.IGNORECASE)
_SPICES_SPACE = re.compile(r"^spices\s+(.+)$", re.IGNORECASE)

_SKIP_HEAD = re.compile(
    r"\b(babyfood|applebee|restaurant|industrial|separable|and|with)\b",
    re.IGNORECASE,
)

# Inert part / morphology suffixes (M4). Residual must already resolve.
_PART_SUFFIX = frozenset({
    "leaves", "leaf", "fillets", "fillet", "steaks", "steak",
    "stalks", "stalk", "sprigs", "sprig", "pods", "pod",
    "bulb", "bulbs", "cloves", "flakes", "strips",
    "coarse", "fine", "powder", "strands", "chunks", "pearls",
})

# Geographic / breed adjectives (M3). Drop leading token only.
_GEO_PREFIX = frozenset({
    "atlantic", "pacific", "alaska", "alaskan", "norwegian", "scottish",
    "wild", "farmed",
})

# Color / grade adjectives on allowlisted commodity heads only
# (``white rice`` → ``rice``). Never ``white chocolate`` (not in heads).
_COLOR_PREFIX = frozenset({
    "white", "brown", "red", "black", "green", "yellow", "dark", "light",
})
_COLOR_STRIP_HEADS = frozenset({
    "rice", "flour", "sugar", "pepper", "onion", "onions", "bean", "beans",
    "corn", "potato", "potatoes", "tea", "wine", "vinegar", "mustard",
    "sesame", "cabbage", "quinoa", "lentil", "lentils", "pea", "peas",
})

# Head-first grocery phrasing (``salt himalayan``, ``vinegar balsamic``).
# Rotate the head noun to the end so Adj+Noun forms can resolve.
_HEAD_FIRST_NOUNS = frozenset({
    "salt", "sugar", "vinegar", "oil", "flour", "milk", "rice", "pepper",
    "seed", "seeds", "syrup", "sauce", "cheese", "bean", "beans", "pea",
    "peas", "onion", "onions", "potato", "potatoes", "squash", "tea",
    "wine", "water", "cream", "yogurt", "butter", "juice", "paste",
    "starch", "broth", "stock", "bouillon",
})

# Never strip these (false-Safe / wrong identity risk).
_FORBIDDEN_STRIP = frozenset({
    "juice", "puree", "purée", "paste", "butter", "chestnut", "chestnuts",
    "oil", "sauce", "broth", "stock", "powder", "extract", "syrup",
})


def _accept_head(head: str) -> str | None:
    head = normalize_ingredient_key(head) if head else ""
    if not head or _SKIP_HEAD.search(head):
        return None
    if " and " in head or " with " in head:
        return None
    if len(head.split()) > 4:
        return None
    if not (2 <= len(head) <= 40):
        return None
    return head


def simple_commodity_head(name: str) -> str | None:
    """Return a short chat key for a long dump name, or None if unsafe."""
    raw = (name or "").strip()
    if not raw:
        return None

    # Prefer original punctuation: multi-comma forms must refuse before
    # normalize collapses them into spaces.
    if "," in raw:
        if raw.count(",") != 1:
            return None
        m = _SPICES_COMMA.match(raw)
        if m:
            head = re.sub(r",?\s*dried$", "", m.group(1), flags=re.I).strip()
            return _accept_head(head) if "," not in head else None
        m = _SIMPLE_PREP_COMMA.match(raw)
        if not m:
            return None
        return _accept_head(m.group(1).strip())

    n = normalize_ingredient_key(raw)
    if not n or _SKIP_HEAD.search(n):
        return None

    m = _SPICES_SPACE.match(n)
    if m:
        head = re.sub(r"\s+dried$", "", m.group(1)).strip()
        return _accept_head(head)

    m = _SIMPLE_PREP_SPACE.match(n)
    if not m:
        return None
    return _accept_head(m.group(1).strip())


def facet_reduction_candidates(name: str) -> list[str]:
    """Allowlisted shorter forms; caller must confirm residual resolves.

    Order: prep-head, trailing part strip, leading geo strip, then combinations.
    Never returns juice/puree/butter-style reductions.
    """
    n = normalize_ingredient_key(name or "")
    if not n:
        return []
    out: list[str] = []
    seen: set[str] = {n}

    def _add(cand: str | None) -> None:
        if not cand or cand in seen:
            return
        if any(tok in _FORBIDDEN_STRIP for tok in cand.split()):
            # Still allow the candidate itself if it's a known full phrase;
            # forbidden check is on *stripped tokens*, not residual content.
            pass
        seen.add(cand)
        out.append(cand)

    head = simple_commodity_head(n)
    _add(head)

    parts = n.split()
    if len(parts) >= 2:
        last = parts[-1]
        if last in _PART_SUFFIX and last not in _FORBIDDEN_STRIP:
            residual = " ".join(parts[:-1]).strip()
            if residual and residual not in _FORBIDDEN_STRIP:
                _add(_accept_head(residual) or residual)
        first = parts[0]
        if first in _GEO_PREFIX and len(parts) >= 2:
            residual = " ".join(parts[1:]).strip()
            _add(_accept_head(residual) or residual)
            # atlantic salmon fillets → salmon fillets → salmon
            if len(parts) >= 3 and parts[-1] in _PART_SUFFIX:
                mid = " ".join(parts[1:-1]).strip()
                _add(_accept_head(mid) or mid)
        if (
            first in _COLOR_PREFIX
            and len(parts) == 2
            and parts[1] in _COLOR_STRIP_HEADS
        ):
            _add(parts[1])
        # salt himalayan → himalayan salt; vinegar apple cider → apple cider vinegar
        if first in _HEAD_FIRST_NOUNS and len(parts) >= 2:
            rotated = " ".join(parts[1:] + parts[:1])
            _add(normalize_ingredient_key(rotated) or rotated)

    return out


def extra_index_keys_for_label(label: str) -> list[str]:
    """Keys to register alongside a label (normalized label + optional head)."""
    keys: list[str] = []
    norm = normalize_ingredient_key(label or "")
    if norm:
        keys.append(norm)
    head = simple_commodity_head(label or "")
    if head and head not in keys:
        keys.append(head)
    return keys


def iter_unique_heads(labels: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        for key in extra_index_keys_for_label(label):
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out
