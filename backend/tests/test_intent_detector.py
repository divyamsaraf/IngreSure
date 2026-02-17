"""
Tests for the intent detector and response composer.
Covers conversational cases, profile persistence, mixed intents, and edge cases.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.intent_detector import detect_intent, ParsedIntent


# ===== MIXED intent: profile + ingredient ====================================

class TestMixedIntent:
    """'I am Jain can I eat eggs?' and similar mixed queries."""

    def test_jain_can_i_eat_eggs(self):
        result = detect_intent("I am Jain can I eat eggs?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        assert "eggs" in [i.lower() for i in result.ingredients]

    def test_im_vegan_is_cheese_okay(self):
        result = detect_intent("I'm vegan. Is cheese okay?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Vegan"
        assert any("cheese" in i.lower() for i in result.ingredients)

    def test_i_follow_halal_can_i_eat_pork(self):
        result = detect_intent("I follow halal, can I eat pork?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Halal"
        assert any("pork" in i.lower() for i in result.ingredients)

    def test_i_am_hindu_veg_is_fish_safe(self):
        result = detect_intent("I am Hindu Veg. Is fish safe?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Hindu Veg"
        assert any("fish" in i.lower() for i in result.ingredients)

    def test_im_kosher_can_i_have_shellfish(self):
        result = detect_intent("I'm kosher, can I have shellfish?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Kosher"
        assert any("shellfish" in i.lower() for i in result.ingredients)

    def test_jain_diet_bread_with_eggs(self):
        result = detect_intent("I follow Jain diet. Is bread with eggs ok?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        # Should extract both bread and eggs
        lower_ings = [i.lower() for i in result.ingredients]
        assert any("bread" in i for i in lower_ings) or any("egg" in i for i in lower_ings)


# ===== INGREDIENT_QUERY ======================================================

class TestIngredientQuery:
    """Queries about specific ingredients (no profile update)."""

    def test_can_i_eat_eggs(self):
        result = detect_intent("Can I eat eggs?")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("egg" in i.lower() for i in result.ingredients)

    def test_is_cheese_safe(self):
        result = detect_intent("Is cheese safe?")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("cheese" in i.lower() for i in result.ingredients)

    def test_are_eggs_and_milk_ok(self):
        result = detect_intent("Are eggs and milk ok?")
        assert result.intent == "INGREDIENT_QUERY"
        lower = [i.lower() for i in result.ingredients]
        assert any("egg" in i for i in lower)
        assert any("milk" in i for i in lower)

    def test_plain_ingredient_list(self):
        result = detect_intent("eggs, milk, flour, sugar")
        assert result.intent == "INGREDIENT_QUERY"
        assert len(result.ingredients) >= 3

    def test_ingredients_colon_list(self):
        result = detect_intent("Ingredients: water, sugar, wheat flour, eggs, salt")
        assert result.intent == "INGREDIENT_QUERY"
        assert len(result.ingredients) >= 4

    def test_what_about_gelatin(self):
        result = detect_intent("What about gelatin?")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("gelatin" in i.lower() for i in result.ingredients)

    def test_check_collagen(self):
        result = detect_intent("check collagen")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("collagen" in i.lower() for i in result.ingredients)

    def test_is_vanilla_extract_safe(self):
        result = detect_intent("Is vanilla extract safe?")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("vanilla extract" in i.lower() for i in result.ingredients)

    def test_bread_with_eggs_safe(self):
        result = detect_intent("Is bread with eggs safe?")
        assert result.intent == "INGREDIENT_QUERY"
        lower = [i.lower() for i in result.ingredients]
        assert any("bread" in i for i in lower) or any("egg" in i for i in lower)

    def test_single_ingredient(self):
        result = detect_intent("tuna")
        assert result.intent == "INGREDIENT_QUERY"
        assert any("tuna" in i.lower() for i in result.ingredients)


# ===== PROFILE_UPDATE ========================================================

class TestProfileUpdate:
    """Pure profile-update intents (no ingredient query)."""

    def test_i_am_jain(self):
        result = detect_intent("I am Jain")
        assert result.intent == "PROFILE_UPDATE"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        assert not result.ingredients

    def test_im_vegan(self):
        result = detect_intent("I'm vegan")
        assert result.intent == "PROFILE_UPDATE"
        assert result.profile_updates.get("dietary_preference") == "Vegan"

    def test_i_follow_halal(self):
        result = detect_intent("I follow halal")
        assert result.intent == "PROFILE_UPDATE"
        assert result.profile_updates.get("dietary_preference") == "Halal"

    def test_my_diet_is_kosher(self):
        result = detect_intent("My diet is kosher")
        assert result.intent == "PROFILE_UPDATE"
        assert result.profile_updates.get("dietary_preference") == "Kosher"

    def test_update_command(self):
        result = detect_intent("/update dietary_preference Jain")
        assert result.intent == "PROFILE_UPDATE"

    def test_switch_to_vegetarian(self):
        result = detect_intent("switch to vegetarian")
        assert result.intent == "PROFILE_UPDATE"
        assert result.profile_updates.get("dietary_preference") == "Vegetarian"


# ===== GREETING ==============================================================

class TestGreeting:
    def test_hello(self):
        assert detect_intent("Hello").intent == "GREETING"

    def test_hi(self):
        assert detect_intent("hi").intent == "GREETING"

    def test_hey(self):
        assert detect_intent("hey!").intent == "GREETING"

    def test_good_morning(self):
        assert detect_intent("Good morning").intent == "GREETING"


# ===== GENERAL_QUESTION ======================================================

class TestGeneralQuestion:
    def test_what_is_castoreum(self):
        result = detect_intent("What is castoreum?")
        assert result.intent == "GENERAL_QUESTION"

    def test_tell_me_about_gelatin(self):
        result = detect_intent("Tell me about gelatin")
        assert result.intent == "GENERAL_QUESTION"

    def test_empty_query(self):
        result = detect_intent("")
        assert result.intent == "GENERAL_QUESTION"


# ===== ALLERGEN / LIFESTYLE DETECTION ========================================

class TestAllergenLifestyle:
    def test_allergic_to_peanuts(self):
        result = detect_intent("I'm allergic to peanuts, can I eat this granola bar?")
        assert result.has_profile_update
        assert "peanuts" in (result.profile_updates.get("allergens") or [])

    def test_no_alcohol(self):
        result = detect_intent("I don't drink alcohol. Is vanilla extract safe?")
        assert result.has_profile_update
        lifestyle = result.profile_updates.get("lifestyle", [])
        assert "no alcohol" in lifestyle
        assert any("vanilla" in i.lower() for i in result.ingredients)


# ===== EDGE CASES ============================================================

class TestThirdPersonQueries:
    """Third-person and indirect diet+ingredient queries."""

    def test_can_jain_eat_onion(self):
        """THE critical bug: 'can jain eat onion?' should detect Jain + onion."""
        result = detect_intent("can jain eat onion?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        assert any("onion" in i.lower() for i in result.ingredients)

    def test_can_vegans_eat_honey(self):
        result = detect_intent("can vegans eat honey?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Vegan"
        assert any("honey" in i.lower() for i in result.ingredients)

    def test_is_pork_halal(self):
        result = detect_intent("is pork halal?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Halal"
        assert any("pork" in i.lower() for i in result.ingredients)

    def test_is_gelatin_kosher(self):
        result = detect_intent("is gelatin kosher?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Kosher"
        assert any("gelatin" in i.lower() for i in result.ingredients)

    def test_are_eggs_vegan(self):
        result = detect_intent("are eggs vegan?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Vegan"
        assert any("egg" in i.lower() for i in result.ingredients)

    def test_does_jain_allow_garlic(self):
        result = detect_intent("does jain allow garlic?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        assert any("garlic" in i.lower() for i in result.ingredients)

    def test_can_a_hindu_veg_person_eat_fish(self):
        result = detect_intent("can a hindu veg person eat fish?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Hindu Veg"
        assert any("fish" in i.lower() for i in result.ingredients)

    def test_is_onion_jain(self):
        result = detect_intent("is onion jain?")
        assert result.intent == "MIXED"
        assert any("onion" in i.lower() for i in result.ingredients)

    def test_is_honey_vegan(self):
        result = detect_intent("is honey vegan?")
        assert result.intent == "MIXED"
        assert any("honey" in i.lower() for i in result.ingredients)


class TestEdgeCases:
    def test_fish_not_mangled(self):
        """'fish' should not be destroyed by stopword removal."""
        result = detect_intent("Is fish safe?")
        assert any("fish" in i.lower() for i in result.ingredients)

    def test_raisins_not_mangled(self):
        """'raisins' should survive extraction."""
        result = detect_intent("Can I eat raisins?")
        assert any("raisin" in i.lower() for i in result.ingredients)

    def test_asparagus_survives(self):
        result = detect_intent("Is asparagus safe?")
        assert any("asparagus" in i.lower() for i in result.ingredients)

    def test_multiple_sentences(self):
        result = detect_intent("I am Jain. Can I eat honey and eggs?")
        assert result.intent == "MIXED"
        assert result.profile_updates.get("dietary_preference") == "Jain"
        lower = [i.lower() for i in result.ingredients]
        assert any("egg" in i for i in lower) or any("honey" in i for i in lower)


# ===== INTEGRATION: Intent → Compliance (requires compliance engine) =========

class TestIntentToCompliance:
    """End-to-end: intent detection → compliance evaluation."""

    def test_jain_eggs_not_safe(self):
        """'I am Jain can I eat eggs?' → eggs NOT_SAFE for Jain."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("I am Jain can I eat eggs?")
        assert parsed.intent == "MIXED"
        assert parsed.profile_updates.get("dietary_preference") == "Jain"
        assert parsed.ingredients

        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        assert "jain" in rids

        verdict = run_new_engine_chat(
            parsed.ingredients,
            user_profile=profile,
            restriction_ids=rids,
        )
        assert verdict.status == VerdictStatus.NOT_SAFE
        assert verdict.confidence_score > 0.5

    def test_vegan_cheese_not_safe(self):
        """'I am vegan. Is cheese okay?' → cheese NOT_SAFE for vegan."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("I am vegan. Is cheese okay?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Vegan")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_jain_rice_safe(self):
        """'I am Jain. Can I eat rice?' → rice SAFE for Jain."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("I am Jain. Can I eat rice?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.SAFE

    def test_halal_pork_not_safe(self):
        """'I follow halal, can I eat pork?' → pork NOT_SAFE for halal."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("I follow halal, can I eat pork?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Halal")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_vegetarian_tofu_safe(self):
        """'Can I eat tofu?' with vegetarian profile → SAFE."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("Can I eat tofu?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Vegetarian")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.SAFE

    def test_jain_onion_not_safe(self):
        """Onion NOT_SAFE for Jain."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("Can I eat onion?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_no_restrictions_everything_safe(self):
        """With 'No rules', common ingredients should be SAFE."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        profile = UserProfile(user_id="test")  # No rules by default
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(
            ["eggs", "milk", "beef"],
            user_profile=profile,
            restriction_ids=rids,
        )
        # No restrictions → everything should be SAFE
        assert verdict.status == VerdictStatus.SAFE

    def test_can_jain_eat_onion_not_safe(self):
        """THE critical bug: 'can jain eat onion?' → onion NOT_SAFE for Jain."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("can jain eat onion?")
        assert parsed.intent == "MIXED"
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_is_pork_halal_not_safe(self):
        """'is pork halal?' → pork NOT_SAFE for Halal."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("is pork halal?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Halal")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_can_vegans_eat_honey_not_safe(self):
        """Honey NOT_SAFE for vegan (insect_derived)."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("can vegans eat honey?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Vegan")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_is_gelatin_kosher_not_safe(self):
        """Gelatin NOT_SAFE for Kosher (animal_species=pig typically)."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("is gelatin kosher?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Kosher")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        # Gelatin is animal-derived; kosher restricts pig-derived
        assert verdict.status in (VerdictStatus.NOT_SAFE, VerdictStatus.UNCERTAIN)

    def test_jain_garlic_not_safe(self):
        """Garlic NOT_SAFE for Jain."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("does jain allow garlic?")
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        verdict = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert verdict.status == VerdictStatus.NOT_SAFE

    def test_input_validation_rejects_sentences(self):
        """Sentences should not be sent to the API as ingredient names."""
        from core.ontology.ingredient_registry import _is_valid_ingredient_input
        assert _is_valid_ingredient_input("onion") is True
        assert _is_valid_ingredient_input("chicken breast") is True
        assert _is_valid_ingredient_input("can jain eat onion") is False
        assert _is_valid_ingredient_input("is pork halal safe to eat") is False
        assert _is_valid_ingredient_input("does vegan allow this ingredient") is False


class TestComprehensiveRestrictions:
    """End-to-end compliance tests for ALL dietary/religious restrictions."""

    @staticmethod
    def _verdict(diet: str, ingredients: list):
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        profile = UserProfile(user_id="test")
        profile.update_merge(dietary_preference=diet)
        rids = user_profile_model_to_restriction_ids(profile)
        return run_new_engine_chat(ingredients, user_profile=profile, restriction_ids=rids)

    # === VEGAN ===
    def test_vegan_milk_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["milk"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegan_egg_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["egg"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegan_honey_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["honey"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegan_gelatin_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["gelatin"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegan_rice_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["rice"])
        assert v.status == VerdictStatus.SAFE

    def test_vegan_tofu_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegan", ["tofu"])
        assert v.status == VerdictStatus.SAFE

    # === VEGETARIAN ===
    def test_vegetarian_chicken_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegetarian", ["chicken"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegetarian_fish_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegetarian", ["fish"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegetarian_gelatin_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegetarian", ["gelatin"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_vegetarian_milk_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegetarian", ["milk"])
        assert v.status == VerdictStatus.SAFE

    def test_vegetarian_egg_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Vegetarian", ["egg"])
        assert v.status == VerdictStatus.SAFE

    # === HALAL ===
    def test_halal_pork_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["pork"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_halal_lard_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["lard"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_halal_gelatin_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["gelatin"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_halal_alcohol_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["wine"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_halal_chicken_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["chicken"])
        assert v.status == VerdictStatus.SAFE

    def test_halal_lamb_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Halal", ["lamb"])
        assert v.status == VerdictStatus.SAFE

    # === KOSHER ===
    def test_kosher_pork_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Kosher", ["pork"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_kosher_shellfish_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Kosher", ["shrimp"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_kosher_gelatin_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Kosher", ["gelatin"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_kosher_chicken_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Kosher", ["chicken"])
        assert v.status == VerdictStatus.SAFE

    # === JAIN ===
    def test_jain_onion_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["onion"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_garlic_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["garlic"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_egg_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["egg"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_potato_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["potato"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_mushroom_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["mushroom"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_honey_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["honey"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_gelatin_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["gelatin"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_jain_rice_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["rice"])
        assert v.status == VerdictStatus.SAFE

    def test_jain_wheat_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["wheat"])
        assert v.status == VerdictStatus.SAFE

    def test_jain_milk_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["milk"])
        assert v.status == VerdictStatus.SAFE

    def test_jain_wine_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Jain", ["wine"])
        assert v.status == VerdictStatus.NOT_SAFE

    # === HINDU VEG ===
    def test_hindu_veg_beef_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Veg", ["beef"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_hindu_veg_egg_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Veg", ["egg"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_hindu_veg_fish_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Veg", ["fish"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_hindu_veg_milk_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Veg", ["milk"])
        assert v.status == VerdictStatus.SAFE

    def test_hindu_veg_ghee_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Veg", ["ghee"])
        assert v.status == VerdictStatus.SAFE

    # === HINDU NON-VEG ===
    def test_hindu_nonveg_beef_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Non Vegetarian", ["beef"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_hindu_nonveg_pork_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Non Vegetarian", ["pork"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_hindu_nonveg_chicken_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Non Vegetarian", ["chicken"])
        assert v.status == VerdictStatus.SAFE

    def test_hindu_nonveg_lamb_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Hindu Non Vegetarian", ["lamb"])
        assert v.status == VerdictStatus.SAFE

    # === PESCATARIAN ===
    def test_pescatarian_chicken_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Pescatarian", ["chicken"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_pescatarian_beef_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Pescatarian", ["beef"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_pescatarian_fish_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Pescatarian", ["fish"])
        assert v.status == VerdictStatus.SAFE

    def test_pescatarian_salmon_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Pescatarian", ["salmon"])
        assert v.status == VerdictStatus.SAFE

    # === LACTO-VEGETARIAN ===
    def test_lacto_veg_egg_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Lacto Vegetarian", ["egg"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_lacto_veg_chicken_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Lacto Vegetarian", ["chicken"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_lacto_veg_milk_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Lacto Vegetarian", ["milk"])
        assert v.status == VerdictStatus.SAFE

    # === OVO-VEGETARIAN ===
    def test_ovo_veg_milk_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Ovo Vegetarian", ["milk"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_ovo_veg_egg_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Ovo Vegetarian", ["egg"])
        assert v.status == VerdictStatus.SAFE

    # === GLUTEN-FREE ===
    def test_gluten_free_wheat_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Gluten-Free", ["wheat"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_gluten_free_barley_not_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Gluten-Free", ["barley"])
        assert v.status == VerdictStatus.NOT_SAFE

    def test_gluten_free_rice_safe(self):
        from core.models.verdict import VerdictStatus
        v = self._verdict("Gluten-Free", ["rice"])
        assert v.status == VerdictStatus.SAFE

    # === CONVERSATIONAL NL → COMPLIANCE FLOW ===
    def test_can_jain_eat_onion_full_flow(self):
        """Full conversational flow: 'can jain eat onion?' → MIXED → NOT_SAFE."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("can jain eat onion?")
        assert parsed.intent == "MIXED"
        assert parsed.profile_updates.get("dietary_preference") == "Jain"
        assert any("onion" in i.lower() for i in parsed.ingredients)

        profile = UserProfile(user_id="flow_test")
        profile.update_merge(dietary_preference=parsed.profile_updates["dietary_preference"])
        rids = user_profile_model_to_restriction_ids(profile)
        v = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert v.status == VerdictStatus.NOT_SAFE

    def test_is_mushroom_jain_full_flow(self):
        """'is mushroom jain?' → MIXED → NOT_SAFE (fungal)."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("is mushroom jain?")
        assert parsed.intent == "MIXED"
        profile = UserProfile(user_id="flow_test")
        profile.update_merge(dietary_preference="Jain")
        rids = user_profile_model_to_restriction_ids(profile)
        v = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert v.status == VerdictStatus.NOT_SAFE

    def test_can_vegans_eat_honey_full_flow(self):
        """'can vegans eat honey?' → MIXED → NOT_SAFE."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("can vegans eat honey?")
        assert parsed.intent == "MIXED"
        profile = UserProfile(user_id="flow_test")
        profile.update_merge(dietary_preference="Vegan")
        rids = user_profile_model_to_restriction_ids(profile)
        v = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert v.status == VerdictStatus.NOT_SAFE

    def test_does_halal_allow_wine_full_flow(self):
        """'does halal allow wine?' → MIXED → NOT_SAFE."""
        from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
        from core.models.user_profile import UserProfile
        from core.models.verdict import VerdictStatus

        parsed = detect_intent("does halal allow wine?")
        assert parsed.intent == "MIXED"
        profile = UserProfile(user_id="flow_test")
        profile.update_merge(dietary_preference="Halal")
        rids = user_profile_model_to_restriction_ids(profile)
        v = run_new_engine_chat(parsed.ingredients, user_profile=profile, restriction_ids=rids)
        assert v.status == VerdictStatus.NOT_SAFE
