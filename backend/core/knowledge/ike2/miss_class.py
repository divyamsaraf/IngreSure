"""Lightweight L5 miss-class tagging (design §9.3.1 observability).

Tags never change the verdict — they prioritize offline promote / alias work.
"""
from __future__ import annotations

import re

from core.normalization.normalizer import normalize_ingredient_key

_GEO = re.compile(
    r"\b(atlantic|pacific|alaska|alaskan|norwegian|scottish)\b",
    re.I,
)
_CUT = re.compile(
    r"\b(brisket|chuck|flank|sirloin|ribeye|tenderloin|chops?|mince|"
    r"ribs?|shank|roast|fillets?|steaks?|wings?|thighs?|breast|belly)\b",
    re.I,
)
_PART = re.compile(
    r"\b(leaves?|stalks?|sprigs?|pods?|bulbs?|cloves|flakes|roots?)\b",
    re.I,
)
_FORM = re.compile(
    r"\b(juice|puree|purée|paste|powder|sauce|broth|stock|syrup|jam|jelly)\b",
    re.I,
)
_ANIMAL_COMPOUND = re.compile(
    r"\b(bacon fat|bacon grease|chicken fat|duck fat|beef tallow|suet)\b",
    re.I,
)
_DAIRY_VARIETY = re.compile(
    r"\b(camembert|brie|cheddar|gouda|feta|mozzarella|parmesan|stilton|"
    r"emmental|edam|comte|comté|cotija|quark|colby|fontina)\b",
    re.I,
)
_SEAWEED = re.compile(r"\b(kombu|nori|wakame|kelp|dulse|hijiki)\b", re.I)


def classify_miss_class(atom: str) -> str:
    """Return M1–M12-ish tag for an unresolved atom."""
    raw = (atom or "").strip()
    n = normalize_ingredient_key(raw)
    if not n:
        return "M1_absent"

    if "'" in raw or "\u2019" in raw:
        return "M8_orthography"
    if _ANIMAL_COMPOUND.search(n):
        return "M7_compound_animal"
    if _FORM.search(n):
        return "M5_processed_form"
    if _CUT.search(n) and len(n.split()) >= 2:
        return "M2_cut_part"
    if _GEO.search(n):
        return "M3_species_geo"
    if _PART.search(n) and len(n.split()) >= 2:
        return "M4_morphology"
    if _DAIRY_VARIETY.search(n) or _SEAWEED.search(n):
        # Variety/identity often absent from ontology → promote seed.
        return "M1_absent" if len(n.split()) == 1 else "M6_dairy_variety"
    if len(n.split()) == 1:
        return "M1_absent"
    return "M1_absent"
