"""End-to-end safety against the live (local) DB: a real peanut group, visible
through ike2_v_alias_resolution, must drive a non-SAFE verdict for a peanut
allergy via resolve -> seam -> evaluate. This closes the data loop that the
faked-store tests cannot: it proves the actual view projects the flag column and
that the flag survives the whole pipeline.
"""
import os

import pytest

from core.knowledge.ike2 import resolver, rules
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import Verdict

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"), reason="needs local supabase"
)

_ALIAS = "ike2_test_peanut_alias"
_CANONICAL = "ike2_test_peanut_group"


@pytest.fixture
def seed_peanut(db_admin):
    client = db_admin

    def _cleanup():
        client.table("ike2_aliases").delete().eq(
            "normalized_alias", _ALIAS
        ).execute()
        groups = (
            client.table("ike2_ingredient_groups")
            .select("id")
            .eq("canonical_name", _CANONICAL)
            .execute()
            .data
        )
        for grp in groups:
            client.table("ike2_ingredients").delete().eq(
                "group_id", grp["id"]
            ).execute()
        client.table("ike2_ingredient_groups").delete().eq(
            "canonical_name", _CANONICAL
        ).execute()

    _cleanup()
    grp = (
        client.table("ike2_ingredient_groups")
        .insert(
            {
                "canonical_name": _CANONICAL,
                "plant_origin": True,
                "peanut_source": True,
                "knowledge_state": "AUTO_CLASSIFIED",
            }
        )
        .execute()
        .data[0]
    )
    ing = (
        client.table("ike2_ingredients")
        .insert({"group_id": grp["id"], "normalized_name": _CANONICAL})
        .execute()
        .data[0]
    )
    client.table("ike2_aliases").insert(
        {
            "normalized_alias": _ALIAS,
            "ingredient_id": ing["id"],
            "alias_type": "common",
        }
    ).execute()
    yield
    _cleanup()


def test_real_peanut_row_is_never_safe_for_peanut_allergy(seed_peanut):
    resolved = resolver.resolve(_ALIAS, region=None)
    ci = to_compliance_input(resolved)
    profile = type("P", (), {"restrictions": {"peanut_allergy": "medical"}})()
    result = evaluate([ci], profile, rules.seeded_rules())
    assert result.verdict != Verdict.SAFE
