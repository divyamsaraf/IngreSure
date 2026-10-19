"""Item 2 Prompt 5: IKE-2 merge_groups + rollback_snapshot."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.knowledge.ike2.merge_groups import MergeResult, merge_groups


@dataclass
class FakeIke2Store:
    """In-memory stand-in for ike2_* tables (no Supabase)."""

    groups: dict[str, dict] = field(default_factory=dict)
    ingredients: dict[str, dict] = field(default_factory=dict)
    aliases: dict[str, dict] = field(default_factory=dict)
    merges: list[dict] = field(default_factory=list)
    _seq: int = 0

    def _next(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}{self._seq}"

    def get_group(self, group_id: str) -> dict | None:
        return self.groups.get(group_id)

    def list_ingredients(self, group_id: str, *, active_only: bool = True) -> list[dict]:
        rows = [r for r in self.ingredients.values() if r["group_id"] == group_id]
        if active_only:
            rows = [r for r in rows if not r.get("superseded_by")]
        return list(rows)

    def list_aliases(self, ingredient_id: str) -> list[dict]:
        return [a for a in self.aliases.values() if a["ingredient_id"] == ingredient_id]

    def update_group_flags(self, group_id: str, flags: dict[str, Any]) -> None:
        g = self.groups[group_id]
        g.update(flags)

    def reassign_ingredient_group(self, ingredient_id: str, new_group_id: str) -> None:
        self.ingredients[ingredient_id]["group_id"] = new_group_id

    def supersede_ingredient(self, ingredient_id: str, keeper_ingredient_id: str) -> None:
        self.ingredients[ingredient_id]["superseded_by"] = keeper_ingredient_id

    def retarget_alias(self, alias_id: str, new_ingredient_id: str) -> None:
        self.aliases[alias_id]["ingredient_id"] = new_ingredient_id

    def supersede_group(self, from_group_id: str, into_group_id: str) -> None:
        self.groups[from_group_id]["superseded_by"] = into_group_id

    def insert_merge_audit(
        self,
        *,
        from_group_id: str,
        into_group_id: str,
        rollback_snapshot: dict,
    ) -> str:
        mid = self._next("m")
        self.merges.append(
            {
                "id": mid,
                "from_group_id": from_group_id,
                "into_group_id": into_group_id,
                "rollback_snapshot": rollback_snapshot,
            }
        )
        return mid


def _seed_pair(store: FakeIke2Store) -> tuple[str, str]:
    """Keeper milk (no fish) + mergee whey (dairy + fish mistaken) for OR merge."""
    into = store._next("g")
    frm = store._next("g")
    store.groups[into] = {
        "id": into,
        "canonical_name": "milk",
        "animal_origin": True,
        "dairy_source": True,
        "fish_source": False,
        "egg_source": False,
        "plant_origin": False,
        "knowledge_state": "AUTO_CLASSIFIED",
        "superseded_by": None,
    }
    store.groups[frm] = {
        "id": frm,
        "canonical_name": "whey powder duplicate",
        "animal_origin": True,
        "dairy_source": True,
        "fish_source": True,  # most-restrictive must OR onto keeper
        "egg_source": False,
        "plant_origin": False,
        "knowledge_state": "DISCOVERED",
        "superseded_by": None,
    }
    i_keep = store._next("i")
    i_merge = store._next("i")
    i_unique = store._next("i")
    store.ingredients[i_keep] = {
        "id": i_keep,
        "group_id": into,
        "normalized_name": "milk",
        "superseded_by": None,
    }
    store.ingredients[i_merge] = {
        "id": i_merge,
        "group_id": frm,
        "normalized_name": "milk",  # collide → supersede + retarget aliases
        "superseded_by": None,
    }
    store.ingredients[i_unique] = {
        "id": i_unique,
        "group_id": frm,
        "normalized_name": "whey",
        "superseded_by": None,
    }
    a1 = store._next("a")
    a2 = store._next("a")
    store.aliases[a1] = {
        "id": a1,
        "normalized_alias": "whole milk",
        "ingredient_id": i_keep,
    }
    store.aliases[a2] = {
        "id": a2,
        "normalized_alias": "lait",
        "ingredient_id": i_merge,
    }
    return into, frm


def test_dry_run_does_not_mutate_store():
    store = FakeIke2Store()
    into, frm = _seed_pair(store)
    result = merge_groups(store, into_group_id=into, from_group_id=frm, dry_run=True)
    assert isinstance(result, MergeResult)
    assert result.dry_run is True
    assert result.applied is False
    assert store.groups[frm].get("superseded_by") is None
    assert store.merges == []
    assert result.rollback_snapshot["from_group_id"] == frm
    assert result.rollback_snapshot["into_group_id"] == into


def test_apply_ors_flags_retargets_aliases_supersedes_mergee():
    store = FakeIke2Store()
    into, frm = _seed_pair(store)
    result = merge_groups(store, into_group_id=into, from_group_id=frm, dry_run=False)
    assert result.applied is True
    assert result.dry_run is False
    assert store.groups[frm]["superseded_by"] == into
    assert store.groups[into]["fish_source"] is True  # OR from mergee
    assert store.groups[into]["dairy_source"] is True

    superseded = [
        i
        for i in store.ingredients.values()
        if i.get("superseded_by") and i["normalized_name"] == "milk"
    ]
    assert len(superseded) == 1
    whey = next(i for i in store.ingredients.values() if i["normalized_name"] == "whey")
    assert whey["group_id"] == into

    lait = next(a for a in store.aliases.values() if a["normalized_alias"] == "lait")
    keeper_milk = next(
        i
        for i in store.ingredients.values()
        if i["normalized_name"] == "milk" and not i.get("superseded_by")
    )
    assert lait["ingredient_id"] == keeper_milk["id"]
    assert len(store.merges) == 1
    assert store.merges[0]["from_group_id"] == frm
    assert store.merges[0]["into_group_id"] == into


def test_rollback_snapshot_round_trip_fields():
    store = FakeIke2Store()
    into, frm = _seed_pair(store)
    result = merge_groups(store, into_group_id=into, from_group_id=frm, dry_run=False)
    snap = result.rollback_snapshot
    assert snap["from_group"]["id"] == frm
    assert snap["into_group_before"]["id"] == into
    assert snap["into_group_before"]["fish_source"] is False
    assert any(a["normalized_alias"] == "lait" for a in snap["aliases_retargeted"])
    assert any(i["normalized_name"] == "whey" for i in snap["ingredients_moved"])
    assert any(i["normalized_name"] == "milk" for i in snap["ingredients_superseded"])
    # Snapshot stored on audit row identically
    assert store.merges[0]["rollback_snapshot"] == snap


def test_merge_never_clears_keeper_positive_flag():
    store = FakeIke2Store()
    into, frm = _seed_pair(store)
    store.groups[frm]["dairy_source"] = False  # mergee weaker on dairy
    result = merge_groups(store, into_group_id=into, from_group_id=frm, dry_run=False)
    assert result.applied
    assert store.groups[into]["dairy_source"] is True
