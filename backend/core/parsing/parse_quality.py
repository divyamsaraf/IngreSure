"""Parse-quality signals that cap a firm SAFE at UNCERTAIN (trust-ceiling analog)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from core.parsing.hazard_lexicon import conservation_misses, hazard_hits_in_text

_TRUNCATION_TAIL = re.compile(
    r"(?:,\s*|;\s*|:\s*|\(\s*|\{\s*|\[\s*|&\s*|/\s*|\band\s+)$",
    re.IGNORECASE,
)
_CONTAINS_FOOTNOTE = re.compile(
    r"(?:^|[.\n])\s*(?:contains|allergens?)\s*[:\-]",
    re.IGNORECASE,
)
# OCR / encoding noise: digits-letter swaps, control chars, odd punctuation density
_OCR_NOISE = re.compile(
    r"[^\x20-\x7E\u00A0-\u024F\u0400-\u04FF\s]|[|]{2,}|(?:lodised|rnilk|0il)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParseQuality:
    ok: bool
    reasons: tuple[str, ...]
    ocr_noise_rate: float


def _paren_balance(text: str) -> bool:
    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for ch in text:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return not stack


def assess_parse_quality(raw: str, atoms: Iterable[str] | None = None) -> ParseQuality:
    """Return whether the label parse is trustworthy enough for firm SAFE."""
    text = (raw or "").strip()
    reasons: list[str] = []
    if not text:
        return ParseQuality(ok=False, reasons=("empty",), ocr_noise_rate=0.0)

    atom_list = [a for a in (atoms or []) if a]
    noise_hits = len(_OCR_NOISE.findall(text))
    ocr_rate = noise_hits / max(len(text), 1)

    if _TRUNCATION_TAIL.search(text) or text.endswith(("...", "…")):
        reasons.append("truncation")
    if not _paren_balance(text):
        reasons.append("unbalanced_parentheses")
    if ocr_rate >= 0.02 or noise_hits >= 3:
        reasons.append("ocr_noise")
    if _CONTAINS_FOOTNOTE.search(text):
        # Footnote present but hazard classes from it still missing from atoms
        # (or atoms empty) → parse failed to surface declared allergens.
        if not atom_list:
            reasons.append("unparsed_contains_footnote")
        else:
            lost = conservation_misses(text, atom_list)
            # Only count when the raw has a contains-section hazard that atoms miss
            footnote = text[max(0, _CONTAINS_FOOTNOTE.search(text).start()) :]
            footnote_hits = hazard_hits_in_text(footnote)
            if footnote_hits & lost:
                reasons.append("unparsed_contains_footnote")

    return ParseQuality(ok=not reasons, reasons=tuple(reasons), ocr_noise_rate=ocr_rate)
