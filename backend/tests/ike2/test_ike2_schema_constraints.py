import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"), reason="needs local supabase"
)


def test_valid_row_accepted(db_admin):
    # A legal row must insert successfully. This is the meaningful RED:
    # before the migration the table does not exist and this fails.
    name = "ike2_test_valid_row"
    db_admin.table("ike2_ingredient_groups").delete().eq(
        "canonical_name", name
    ).execute()
    res = (
        db_admin.table("ike2_ingredient_groups")
        .insert({"canonical_name": name, "animal_origin": True, "dairy_source": True})
        .execute()
    )
    assert res.data and res.data[0]["canonical_name"] == name
    db_admin.table("ike2_ingredient_groups").delete().eq(
        "canonical_name", name
    ).execute()


def test_insect_implies_animal_constraint(db_admin):
    # inserting insect_derived=True with animal_origin=False must be rejected
    with pytest.raises(Exception):
        db_admin.table("ike2_ingredient_groups").insert({
            "canonical_name": "bad_insect_row",
            "animal_origin": False,
            "insect_derived": True,
        }).execute()


def test_verified_requires_source(db_admin):
    with pytest.raises(Exception):
        db_admin.table("ike2_ingredient_groups").insert({
            "canonical_name": "bad_verified_row",
            "knowledge_state": "VERIFIED",
            "primary_source_url": None,
        }).execute()
