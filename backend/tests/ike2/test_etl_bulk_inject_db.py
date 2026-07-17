"""Integration test: SupabaseWriter against the live (local) ike2_* tables."""
import pytest

from core.knowledge.ike2.etl.bulk_inject import SupabaseWriter, inject

_NAMES = ("test bulk carrot zz", "test bulk whey zz")


def _purge(client):
    for name in _NAMES:
        groups = (
            client.table("ike2_ingredient_groups")
            .select("id")
            .eq("canonical_name", name)
            .execute()
            .data
        )
        for grp in groups:
            ings = (
                client.table("ike2_ingredients")
                .select("id")
                .eq("group_id", grp["id"])
                .execute()
                .data
            )
            for ing in ings:
                client.table("ike2_aliases").delete().eq("ingredient_id", ing["id"]).execute()
            client.table("ike2_ingredients").delete().eq("group_id", grp["id"]).execute()
            client.table("ike2_ingredient_groups").delete().eq("id", grp["id"]).execute()


@pytest.fixture
def writer(db_admin, tmp_path):
    _purge(db_admin)
    yield SupabaseWriter(db_admin, reject_report=str(tmp_path / "rejects.json"))
    _purge(db_admin)


def _records():
    return [
        {"canonical_name": "Test Bulk Carrot ZZ", "aliases": ["Test Bulk Carrot ZZ", "tb carrot zz"],
         "plant_origin": True, "regions": ["Global"]},
        {"canonical_name": "Test Bulk Whey ZZ", "aliases": ["Test Bulk Whey ZZ"],
         "animal_origin": True, "dairy_source": True, "regions": ["Global"]},
    ]


def test_bulk_inject_writes_groups_ingredients_aliases(writer, db_admin):
    stats = inject(_records(), "wikidata", writer)
    assert stats.inserted == 2
    assert stats.ingredients == 2
    assert stats.aliases == 3  # carrot has 2 aliases, whey has 1

    grp = writer.get_group("test bulk carrot zz")
    assert grp is not None and grp["plant_origin"] is True

    alias_rows = (
        db_admin.table("ike2_aliases")
        .select("normalized_alias")
        .eq("normalized_alias", "tb carrot zz")
        .execute()
        .data
    )
    assert len(alias_rows) == 1


def test_bulk_inject_is_idempotent_against_db(writer):
    inject(_records(), "wikidata", writer)
    again = inject(_records(), "wikidata", writer)
    assert again.inserted == 0
    assert again.updated == 2
    assert again.aliases == 0  # no duplicate aliases
