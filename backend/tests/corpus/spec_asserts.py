"""Machine-checkable assertions for Step 1 spec IDs.

Each spec file row may include an ``assert`` object. Expanded variants inherit
it and may override. The runner checks only these fields — no prose heuristics.
"""
from __future__ import annotations

# Shared pieces.
_NO5 = {"no_5xx": True}
_OK = {**_NO5, "status_code": 200}
_NS = {**_OK, "verdict_not": ["SAFE"]}
_PRODUCT_NS = {**_NS}  # evaluate-product / chat audit must not be SAFE

BY_ID: dict[str, dict] = {
    "A01": {**_OK, "atoms_contain": ["water", "sugar", "wheat", "milk"], "verdict_in": ["NOT_SAFE"]},
    "A02": {**_OK, "atoms_must_not": ["ingredients", "zutaten"]},
    "A03": {**_OK, "atoms_contain": ["chocolate", "sugar", "cocoa", "milk", "flour"]},
    "A04": {**_OK, "atoms_contain": ["peanut"], "atoms_must_not": ["49.5", "49,5"]},
    "A05": {**_OK, "atoms_must_not": ["ii", "i"]},
    "A06": {**_OK, "atoms_contain": ["milk", "soy"], "verdict_in": ["NOT_SAFE"]},
    "A07": {**_OK},
    "A08": {**_OK},
    "A09": {**_OK},
    "A10": {**_OK, "atoms_contain": ["water"]},
    "A11": {**_OK},
    "A12": {**_NS, "atoms_contain": ["wheat", "milk"]},
    "A13": {**_NS},
    "A14": {**_NS, "verdict_not": ["SAFE"]},
    "A15": {**_OK, "atoms_contain": ["flour", "wheat", "sugar"]},
    "A16": {**_NS},
    "A17": {**_OK, "atoms_contain": ["milk"], "verdict_in": ["NOT_SAFE"]},
    "A18": {**_OK, "atoms_must_not": ["cups", "tbsp"]},
    "A19": {**_OK},
    "A20": {**_OK},
    "A21": {**_OK},
    "A22": {**_NS, "atoms_contain": ["sugar", "lait"]},
    "A23": {**_OK, "verdict_in": ["NOT_SAFE"]},
    "A24": {**_OK, "no_5xx": True},
    "A25": {**_OK},
    "A26": {**_NO5},
    "A27": {**_NO5},
    "A28": {**_OK},
    "A29": {**_NS},
    "A30": {**_OK, "verdict_not": ["SAFE"]},
    "A31": {**_OK},
    "A32": {**_OK, "atoms_contain": ["sugar", "milk"]},
    "A33": {**_NS, "atoms_contain": ["flavor"]},
    "A34": {**_OK, "atoms_must_not": ["ii", "i", "a"]},
    "A35": {
        **_OK,
        "atoms_must_not": ["emulsifier", "thickener", "acidity regulator"],
        "atoms_contain": ["322", "471"],
    },
    "A36": {**_OK, "atoms_must_not": ["emulsifier"], "atoms_contain": ["lecithin", "soya"]},
    "B01": {**_OK, "intent": ["PROFILE_UPDATE", "INGREDIENT_QUERY", "GENERAL_QUESTION"]},
    "B02": {**_OK},
    "B03": {**_OK, "body_contains": ["dairy"]},
    "B04": {**_OK},
    "B05": {**_OK},
    "B06": {**_OK},
    "B07": {**_OK},
    "B08": {**_OK},
    "B09": {**_OK},
    "B10": {**_OK, "verdict_not": ["SAFE"]},
    "B11": {**_OK},
    "B12": {**_OK},
    "B13": {**_OK},
    "B14": {**_OK},
    "B15": {**_OK},
    "B16": {**_OK},
    "C01": {**_OK},
    "C02": {**_OK, "verdict_not": ["SAFE", "NOT_SAFE"]},
    "C03": {**_OK},
    "C04": {**_OK},
    "C05": {**_OK},
    "C06": {**_OK},
    "C07": {**_OK, "body_contains": ["911"], "audit": False},
    "C08": {**_OK, "verdict_not": ["SAFE"]},
    "C09": {**_OK, "audit": False},
    "C10": {**_OK, "verdict_not": ["SAFE"]},
    "C11": {**_OK},
    "C12": {**_OK, "verdict_not": ["SAFE"]},
    "D01": {**_OK, "verdict_not": ["SAFE"]},
    "D02": {**_OK},
    "D03": {**_OK},
    "D04": {**_OK},
    "D05": {**_NS},
    "E01": {**_NO5, "status_code": [400, 422]},
    "E02": {**_NO5},  # variants split: unknown 422, normalised 200
    "E03": {**_NO5, "verdict_not": ["SAFE"]},
    "E04": {**_NO5, "status_code": 413},
    "E05": {**_NO5},
    "E06": {**_OK},
    "R01": {**_OK, "body_contains": ["911"], "audit": False},
    "R02": {**_OK, "atoms_contain": ["flour", "sugar"]},
    "R03": {**_OK},
    "R04": {**_OK, "atoms_contain": ["wheat", "milk"]},
    "R05": {**_NS, "verdict_not": ["SAFE"]},
    "R06": {**_NS, "verdict_not": ["SAFE"]},
}


def for_spec(spec: dict) -> dict:
    sid = spec.get("id") or spec.get("spec_id")
    return dict(BY_ID.get(sid) or _NO5)
