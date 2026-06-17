import os

import pytest


def _is_local(url: str) -> bool:
    return "127.0.0.1" in url or "localhost" in url


@pytest.fixture
def db_admin():
    """Service-role Supabase client for schema/constraint tests.

    SAFETY: refuses to run against anything but a local Supabase so the
    constraint tests (which insert deliberately-invalid rows) can never
    touch a remote/prod database.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        pytest.skip("needs local supabase (SUPABASE_URL + service role key)")
    if not _is_local(url):
        pytest.fail(
            f"refusing to run schema constraint tests against non-local URL: {url!r}"
        )
    from supabase import create_client

    return create_client(url, key)


@pytest.fixture
def seed_yam(db_admin):
    """Seed two 'yam' candidates (IN -> elephant_foot_yam, US -> dioscorea_yam)
    plus disambiguation rows, so region-scoped resolution and ambiguity can be tested.
    Cleans up afterwards."""
    client = db_admin

    def _cleanup():
        client.table("ike2_alias_disambiguation").delete().eq(
            "normalized_alias", "yam"
        ).execute()
        client.table("ike2_aliases").delete().eq("normalized_alias", "yam").execute()
        for name in ("elephant_foot_yam", "dioscorea_yam"):
            groups = (
                client.table("ike2_ingredient_groups")
                .select("id")
                .eq("canonical_name", name)
                .execute()
                .data
            )
            for grp in groups:
                client.table("ike2_ingredients").delete().eq(
                    "group_id", grp["id"]
                ).execute()
            client.table("ike2_ingredient_groups").delete().eq(
                "canonical_name", name
            ).execute()

    _cleanup()

    candidates = [
        ("elephant_foot_yam", "IN"),
        ("dioscorea_yam", "US"),
    ]
    for canonical, region in candidates:
        grp = (
            client.table("ike2_ingredient_groups")
            .insert({"canonical_name": canonical, "plant_origin": True})
            .execute()
            .data[0]
        )
        ing = (
            client.table("ike2_ingredients")
            .insert({"group_id": grp["id"], "normalized_name": canonical})
            .execute()
            .data[0]
        )
        client.table("ike2_aliases").insert(
            {
                "normalized_alias": "yam",
                "ingredient_id": ing["id"],
                "alias_type": "regional",
                "region": region,
            }
        ).execute()
        client.table("ike2_alias_disambiguation").insert(
            {
                "normalized_alias": "yam",
                "context_region": region,
                "ingredient_id": ing["id"],
            }
        ).execute()

    yield
    _cleanup()
