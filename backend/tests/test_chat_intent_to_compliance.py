"""Integration: intent → prepare_chat_ingredients → compliance (TDD for chat path)."""
from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
from core.intent_detector import detect_intent
from core.models.user_profile import UserProfile
from core.models.verdict import VerdictStatus
from core.parsing.chat_ingredients import prepare_chat_ingredients
from tests.test_label_decomposer import BREAD_LABEL


def _verdict_via_chat_path(diet: str, query: str):
    parsed = detect_intent(query)
    prepared = prepare_chat_ingredients(query, parsed)
    profile = UserProfile(user_id="test")
    profile.update_merge(dietary_preference=diet)
    rids = user_profile_model_to_restriction_ids(profile)
    return run_new_engine_chat(
        prepared.eval_names,
        user_profile=profile,
        restriction_ids=rids,
        prepared_decomposed=prepared.decomposed,
    )


def test_bread_label_hindu_vegetarian_no_junk_in_eval():
    query = f"I am Hindu Vegetarian. {BREAD_LABEL}"
    parsed = detect_intent(query)
    prepared = prepare_chat_ingredients(query, parsed)

    assert not any("folic acid]" in n for n in prepared.eval_names)
    assert not any("contains 2%" in n.lower() for n in prepared.eval_names)


def test_bread_label_gluten_free_not_safe_via_chat_path():
    query = f"Check this label for gluten-free:\n{BREAD_LABEL}"
    verdict = _verdict_via_chat_path("Gluten-Free", query)
    assert verdict.status == VerdictStatus.NOT_SAFE
