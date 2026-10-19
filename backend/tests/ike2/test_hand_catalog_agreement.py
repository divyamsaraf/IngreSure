"""Hand truth anchors that name the same thing as an E-number catalog row
must agree on animal_origin, verdict_cap, and uncertainty_flags.

A missing animal_origin is false. A missing verdict_cap is None. Uncertainty
flags compare as a set. A disagreeing pair fails unless it is listed in
REVIEWED_EXCEPTIONS with a written reason. E-codes that the normalizer folds
onto a name (E920 -> l-cysteine) count as a match, same as a catalog alias.
"""
from core.knowledge.ike2 import truth_anchor as ta
from core.knowledge.ike2.e_number_catalog import load_catalog, normalize_e_code
from core.normalization.normalizer import normalize_ingredient_key

# (hand canonical_name, catalog e_code) -> why the documents are allowed to differ.
REVIEWED_EXCEPTIONS = {
    ("soy lecithin", "E322"): (
        "Named soy form of an ambiguous generic code "
        "(soy, egg, or sunflower). The catalog stays uncertain and WARN."
    ),
    ("bone phosphate", "E542"): (
        "Reviewed cache merge, 2026-09-25. Hand keeps firm animal_origin. "
        "Catalog keeps may_be_synthetic_tricalcium_phosphate and WARN, and "
        "lookup(e542) stays unmerged."
    ),
    ("disodium inosinate", "E631"): (
        "Reviewed cache merge, 2026-09-25. Both sides are animal_origin. "
        "Catalog keeps may_be_from_yeast_or_tapioca and WARN. The hand "
        "one-liner does not, so the merge stays visible."
    ),
}


def _hand_by_key():
    out = {}
    for key, fact in ta._ANCHORS.items():
        out[normalize_ingredient_key(key)] = fact
    return out


def _catalog_keys(entry):
    raw = [entry.get("e_code"), entry.get("canonical_name")] + list(entry.get("aliases") or [])
    keys = set()
    for alias in raw:
        if not alias:
            continue
        keys.add(normalize_ingredient_key(str(alias)))
        keys.add(normalize_e_code(str(alias)))
    return keys


def _triple(animal, cap, flags):
    return (
        bool(animal),
        cap,
        tuple(sorted(flags or [])),
    )


def matching_pairs():
    """Unique (hand canonical, e-code, hand fact, catalog entry)."""
    hand_by_key = _hand_by_key()
    seen = set()
    pairs = []
    for entry in load_catalog():
        hits = {}
        for key in _catalog_keys(entry):
            fact = hand_by_key.get(key)
            if fact is not None:
                hits[fact.canonical_name] = fact
        code = entry.get("e_code")
        for canon, fact in hits.items():
            ident = (canon, code)
            if ident in seen:
                continue
            seen.add(ident)
            pairs.append((canon, code, fact, entry))
    return pairs


def _hand_triple(fact):
    flags = fact.flags or {}
    return _triple(
        flags.get("animal_origin"),
        flags.get("verdict_cap"),
        flags.get("uncertainty_flags"),
    )


def _catalog_triple(entry):
    return _triple(
        entry.get("animal_origin"),
        entry.get("verdict_cap"),
        entry.get("uncertainty_flags"),
    )


def test_e_code_named_form_mapping_includes_cysteine():
    found = {(canon, code) for canon, code, _, _ in matching_pairs()}
    assert ("l-cysteine", "E910") in found
    assert ("l-cysteine", "E920") in found


def test_reviewed_exceptions_are_still_real_disagreements():
    by_ident = {
        (canon, code): (fact, entry)
        for canon, code, fact, entry in matching_pairs()
    }
    for ident, reason in REVIEWED_EXCEPTIONS.items():
        assert isinstance(reason, str) and reason.strip(), ident
        fact, entry = by_ident[ident]
        assert _hand_triple(fact) != _catalog_triple(entry), ident
    for pair, reason in REVIEWED_EXCEPTIONS.items():
        assert isinstance(reason, str) and reason.strip(), pair


def test_hand_and_catalog_agree_unless_reviewed():
    known = set(REVIEWED_EXCEPTIONS)
    disagreements = []
    matched = set()
    for canon, code, fact, entry in matching_pairs():
        ident = (canon, code)
        matched.add(ident)
        if _hand_triple(fact) == _catalog_triple(entry):
            continue
        if ident not in known:
            disagreements.append(
                f"{canon} vs {code}: hand {_hand_triple(fact)} catalog {_catalog_triple(entry)}"
            )
    assert disagreements == [], (
        "Hand anchor and E-number catalog disagree. Align them, or add the "
        "pair to REVIEWED_EXCEPTIONS with a written reason.\n"
        + "\n".join(disagreements)
    )
    stale = sorted(known - matched)
    assert stale == [], f"Reviewed exception is not a live pair: {stale}"
