"""TDD regression tests: chat must use label decomposer for pasted labels."""
from __future__ import annotations

import warnings

from core.intent_detector import detect_intent
from core.parsing.chat_ingredients import prepare_chat_ingredients
from tests.test_label_decomposer import BREAD_LABEL


def _bread_query() -> str:
    return f"I am Hindu Vegetarian. {BREAD_LABEL}"


# --- RED baseline: documents the intent-split bug we fix via prepare_chat_ingredients ---


def test_intent_split_alone_produces_bread_label_junk_tokens():
    """Intent _split_ingredients must not be the compliance input for label pastes."""
    parsed = detect_intent(_bread_query())
    names = parsed.ingredients
    assert any("folic acid]" in n for n in names) or any(
        "contains 2%" in n.lower() for n in names
    ), "expected junk tokens from naive intent split (regression guard)"


def test_prepare_chat_ingredients_strips_bread_label_junk_tokens():
    parsed = detect_intent(_bread_query())
    prepared = prepare_chat_ingredients(_bread_query(), parsed)
    names = prepared.eval_names

    assert prepared.decomposed is not None
    assert not any("folic acid]" in n for n in names)
    assert not any("contains 2%" in n.lower() for n in names)
    assert not any(n.lower().startswith("less of each") for n in names)


def test_prepare_chat_ingredients_includes_bread_staples():
    parsed = detect_intent(_bread_query())
    prepared = prepare_chat_ingredients(_bread_query(), parsed)
    names = prepared.eval_names

    assert any("malted barley flour" in n for n in names)
    assert any("enzymes" in n for n in names)


def test_simple_list_uses_compound_expansion_not_decomposer():
    query = "Can I eat burger with chicken?"
    parsed = detect_intent(query)
    prepared = prepare_chat_ingredients(query, parsed)

    assert prepared.decomposed is None
    assert "chicken" in [n.lower() for n in prepared.eval_names]


def test_gelatin_truth_anchor_lists_porcine_species():
    from core.knowledge.ike2 import truth_anchor

    fact = truth_anchor.lookup("gelatin")
    assert fact is not None
    species = fact.flags.get("animal_species") or ""
    assert "porcine" in species.lower()


def test_gelatin_halal_ike2_is_not_safe():
    from core.knowledge.ike2 import resolver, rules
    from core.knowledge.ike2.compliance import evaluate
    from core.knowledge.ike2.seam import to_compliance_input
    from core.knowledge.ike2.verdict import to_external
    from types import SimpleNamespace

    resolved = resolver.resolve("gelatin", None)
    ci = to_compliance_input(resolved)
    profile = SimpleNamespace(restrictions={"halal": "medical"})
    result = evaluate([ci], profile, rules.seeded_rules())
    assert to_external(result.verdict) == "NOT_SAFE"


def test_gelatin_halal_legacy_and_ike2_shadow_align():
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
    from core.knowledge.ike2 import rules as rules_module
    from core.knowledge.ike2.shadow.runner import ike2_external_verdict
    from core.models.user_profile import UserProfile
    from core.models.verdict import VerdictStatus
    from core.parsing.label_decomposer import DecomposedItem

    profile = UserProfile(user_id="test")
    profile.update_merge(dietary_preference="Halal")
    rids = user_profile_model_to_restriction_ids(profile)
    atoms = [DecomposedItem(name="gelatin")]
    seeded = rules_module.seeded_rules()

    verdict = run_new_engine_chat(
        ["gelatin"],
        user_profile=profile,
        restriction_ids=rids,
        use_api_fallback=False,
        prepared_decomposed=atoms,
    )
    ike2 = ike2_external_verdict(
        ["gelatin"], rids, None, decomposed_atoms=atoms, rules=seeded
    )

    assert verdict.status == VerdictStatus.NOT_SAFE
    assert ike2 == "NOT_SAFE"


def test_emit_resolution_metric_skips_without_running_event_loop():
    from unittest.mock import AsyncMock, MagicMock

    from core.knowledge.canonicalizer import CanonicalResolver

    resolver = CanonicalResolver.__new__(CanonicalResolver)
    resolver._db = MagicMock()
    resolver._db.record_resolution_metric = AsyncMock()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolver._emit_resolution_metric(None, source_layer="static")

    resolver._db.record_resolution_metric.assert_not_called()
    assert not any("coroutine" in str(w.message).lower() for w in caught)


def test_run_legacy_diff_forwards_decomposed_atoms(monkeypatch):
    from core.knowledge.ike2.shadow import runner
    from core.knowledge.ike2.shadow.runner import run_legacy_diff
    from core.parsing.label_decomposer import DecomposedItem

    seen: dict = {}

    def _capture(*args, **kwargs):
        seen.update(kwargs)
        return "SAFE"

    monkeypatch.setattr(runner, "legacy_external_verdict", _capture)
    atoms = [DecomposedItem(name="water", trace=True)]
    run_legacy_diff(["ignored"], ["vegan"], None, "SAFE", decomposed_atoms=atoms)

    assert seen.get("decomposed_atoms") is atoms
