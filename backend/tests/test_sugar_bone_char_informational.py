"""Sugar stays firm SAFE for vegan/jain/halal with a bone-char informational note."""
from core.bridge import map_ike2_to_compliance_verdict, run_new_engine_chat
from core.knowledge.ike2.verdict import Verdict
from core.models.verdict import VerdictStatus
from core.response_composer import compose_verdict


def test_sugar_vegan_safe_with_informational_note():
    v = run_new_engine_chat(["sugar"], restriction_ids=["vegan"])
    assert v.status == VerdictStatus.SAFE
    assert "sugar" in [x.lower() for x in v.informational_ingredients]
    text = compose_verdict(v, {"dietary_preference": "vegan"}, ["sugar"])
    assert "bone char" in text.lower()


def test_sugar_dairy_free_no_bone_char_note():
    """Bone-char note is diet-scoped — not for dairy_free alone."""
    v = run_new_engine_chat(["sugar"], restriction_ids=["dairy_free"])
    assert v.status == VerdictStatus.SAFE
    assert "sugar" not in [x.lower() for x in v.informational_ingredients]


def test_beet_sugar_not_informational_for_vegan():
    v = run_new_engine_chat(["beet sugar"], restriction_ids=["vegan"])
    assert v.status == VerdictStatus.SAFE
    assert "beet sugar" not in [x.lower() for x in v.informational_ingredients]
