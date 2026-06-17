import re

from core.normalization.normalizer import normalize_ingredient_key

# Parenthetical qualifiers that point back to the BASE term (e.g. "sugar (from
# beet)" -> "sugar"). Anything else inside parens is treated as the specific
# inner ingredient (e.g. "emulsifier (soy lecithin)" -> "soy lecithin").
_QUALIFIERS = ("from", "derived from", "made from")
_PAREN = re.compile(r"\(([^)]*)\)")


def to_atoms(raw: str) -> list[str]:
    """Sanitize, decompose compounds, split, and normalize a raw ingredient string."""
    if not raw:
        return []
    atoms: list[str] = []
    for segment in re.split(r"[,;]", raw):
        seg = segment.strip()
        if not seg:
            continue
        match = _PAREN.search(seg)
        if match:
            inner = match.group(1).strip()
            base = seg[: match.start()].strip()
            inner_lower = inner.lower()
            if any(inner_lower.startswith(q) for q in _QUALIFIERS):
                chosen = base
            else:
                chosen = inner
        else:
            chosen = seg
        normalized = normalize_ingredient_key(chosen)
        if normalized:
            atoms.append(normalized)
    return atoms
