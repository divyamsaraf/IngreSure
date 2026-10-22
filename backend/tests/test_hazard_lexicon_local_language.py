"""Local-language hazard lexicon: derive tokens, false friends, native review."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external
from core.parsing.hazard_lexicon import hazard_hits_in_text

_REPO = Path(__file__).resolve().parents[2]
_LEXICON = _REPO / "data" / "lexicon" / "hazard_tokens.json"
_REVIEW_LIST = _REPO / "data" / "lexicon" / "NEEDS_NATIVE_REVIEW.md"
_REVIEW_CSV = _REPO / "data" / "lexicon" / "needs_native_review.csv"

EU14_PLUS = frozenset({
    "celery",
    "gluten",
    "crustacean",
    "egg",
    "fish",
    "lupin",
    "dairy",
    "mollusc",
    "mustard",
    "tree_nut",
    "peanut",
    "sesame",
    "soy",
    "sulphite",
})
LANGS = ("fr", "de", "es", "it", "nl", "pl", "pt", "ar", "hi")
FLAG_BY_CLASS = {
    "celery": "celery_source",
    "gluten": "gluten_source",
    "crustacean": "shellfish_source",
    "egg": "egg_source",
    "fish": "fish_source",
    "lupin": "lupin_source",
    "dairy": "dairy_source",
    "mollusc": "shellfish_source",
    "mustard": "mustard_source",
    "tree_nut": "tree_nut_source",
    "peanut": "peanut_source",
    "sesame": "sesame_source",
    "soy": "soy_source",
    "sulphite": "sulphite_source",
}
RID_BY_FLAG = {
    "celery_source": "celery_allergy",
    "gluten_source": "gluten_free",
    "shellfish_source": "shellfish_allergy",
    "egg_source": "egg_free",
    "fish_source": "fish_allergy",
    "lupin_source": "lupin_allergy",
    "dairy_source": "dairy_free",
    "mustard_source": "mustard_allergy",
    "tree_nut_source": "tree_nut_allergy",
    "peanut_source": "peanut_allergy",
    "sesame_source": "sesame_allergy",
    "soy_source": "soy_allergy",
    "sulphite_source": "sulfite_sensitive",
}


def _load() -> dict:
    return json.loads(_LEXICON.read_text(encoding="utf-8"))


def _surfaces(entry: dict) -> list[str]:
    out = [str(entry["surface"])]
    out.extend(str(v) for v in (entry.get("variants") or []))
    return out


def test_lexicon_file_and_review_list_exist():
    assert _LEXICON.is_file()
    assert _REVIEW_LIST.is_file()
    text = _REVIEW_LIST.read_text(encoding="utf-8")
    assert "needs_native_review" in text.lower() or "native review" in text.lower()
    assert all(lang in text for lang in LANGS)


def test_native_review_csv_covers_lexicon_and_groups_languages():
    assert _REVIEW_CSV.is_file()
    with _REVIEW_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols = {
        "language",
        "token",
        "matched_class/context",
        "needs_native_review",
        "false_friend",
        "notes",
    }
    assert cols <= set(rows[0])
    assert all(r["needs_native_review"].lower() == "true" for r in rows)

    expected = set()
    data = _load()
    for cls, payload in data["classes"].items():
        for tok in payload["tokens"]:
            expected.add((tok["lang"], tok["surface"], cls, False))
            for variant in tok.get("variants") or []:
                expected.add((tok["lang"], variant, cls, False))
    for row in data["false_friends"]:
        expected.add(
            (row["lang"], row["surface"], row["would_false_trigger"], True)
        )
    for row in data["negation_words"]:
        expected.add((row["lang"], row["surface"], "negation", False))

    got = {
        (
            r["language"],
            r["token"],
            r["matched_class/context"],
            r["false_friend"].lower() == "true",
        )
        for r in rows
    }
    assert expected <= got

    order = ["hi", "fr", "de", "es", "it", "nl", "pl", "pt", "ar"]
    first_idx = {}
    for i, r in enumerate(rows):
        first_idx.setdefault(r["language"], i)
    ranked = [first_idx[lang] for lang in order if lang in first_idx]
    assert ranked == sorted(ranked)
    assert rows[0]["language"] == "hi"
    assert rows[-1]["language"] == "ar"


def test_every_class_and_language_has_reviewed_tokens():
    data = _load()
    assert data.get("needs_native_review") is True
    assert set(data.get("languages") or []) >= set(LANGS)
    classes = data["classes"]
    assert EU14_PLUS <= set(classes)
    for cls, payload in classes.items():
        assert payload["flag"] == FLAG_BY_CLASS[cls]
        tokens = payload["tokens"]
        langs = {t["lang"] for t in tokens}
        assert set(LANGS) <= langs, f"{cls} missing langs {set(LANGS) - langs}"
        for tok in tokens:
            assert tok.get("needs_native_review") is True, tok
            assert tok.get("surface")
            assert tok.get("lang") in LANGS


def test_false_friends_and_negation_words_marked():
    data = _load()
    friends = {f["surface"].lower() for f in data["false_friends"]}
    for required in (
        "beurre de cacao",
        "lait de coco",
        "kokosmilch",
        "leche de almendra",
    ):
        assert required in friends
    for row in data["false_friends"] + data["negation_words"]:
        assert row.get("needs_native_review") is True
    negs = {n["surface"].lower() for n in data["negation_words"]}
    for word in ("sans", "ohne", "sin", "senza", "zonder", "bez"):
        assert word in negs


def test_live_lexicon_tokens_have_avoid_power():
    """Tokens already in the shared lexicon must Avoid, not merely exist as data."""
    cache.clear()
    rules = rules_module.seeded_rules()
    cases = (
        ("lait", "dairy_source", "dairy_free"),
        ("beurre", "dairy_source", "dairy_free"),
        ("farine de blé", "gluten_source", "gluten_free"),
        ("soja", "soy_source", "soy_allergy"),
        ("arachide", "peanut_source", "peanut_allergy"),
        ("mustard", "mustard_source", "mustard_allergy"),
        ("celery", "celery_source", "celery_allergy"),
        ("lupin", "lupin_source", "lupin_allergy"),
        ("sodium sulphite", "sulphite_source", "sulfite_sensitive"),
    )
    for atom, flag, rid in cases:
        flags = derive_identity_flags(atom)
        assert flags.get(flag) is True, (atom, flag, flags)
        ci = to_compliance_input(resolve(atom, None), query_atom=atom)
        assert ci.flags.get(flag) is True, (atom, flag)
        v = to_external(
            evaluate(
                [ci],
                SimpleNamespace(restrictions={rid: "medical"}),
                rules,
            ).verdict
        )
        assert v == "NOT_SAFE", (atom, rid, v)


def test_named_false_friends_do_not_fire_dairy():
    for text in (
        "beurre de cacao",
        "lait de coco",
        "kokosmilch",
        "leche de almendra",
    ):
        assert "dairy" not in hazard_hits_in_text(text), text
        assert derive_identity_flags(text).get("dairy_source") is not True, text


def test_negation_words_mask_known_live_forms():
    for text in ("sans soja", "ohne soya", "sin soja", "senza soja", "zonder soja"):
        assert "soy" not in hazard_hits_in_text(text), text
