"""IKE-2 group merge with rollback snapshot (Item 2 Prompt 5).

Operates on ``ike2_ingredient_groups`` / ``ike2_ingredients`` / ``ike2_aliases``
via a store protocol (FakeIke2Store in tests; Supabase writer later).

Legacy ``core.knowledge.merge.merge_groups`` is untouched — no dual-write.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS


class Ike2MergeStore(Protocol):
    def get_group(self, group_id: str) -> dict | None: ...

    def list_ingredients(
        self, group_id: str, *, active_only: bool = True
    ) -> list[dict]: ...

    def list_aliases(self, ingredient_id: str) -> list[dict]: ...

    def update_group_flags(self, group_id: str, flags: dict[str, Any]) -> None: ...

    def reassign_ingredient_group(
        self, ingredient_id: str, new_group_id: str
    ) -> None: ...

    def supersede_ingredient(
        self, ingredient_id: str, keeper_ingredient_id: str
    ) -> None: ...

    def retarget_alias(self, alias_id: str, new_ingredient_id: str) -> None: ...

    def supersede_group(self, from_group_id: str, into_group_id: str) -> None: ...

    def insert_merge_audit(
        self,
        *,
        from_group_id: str,
        into_group_id: str,
        rollback_snapshot: dict,
    ) -> str: ...


@dataclass
class MergeResult:
    applied: bool
    dry_run: bool
    into_group_id: str
    from_group_id: str
    merged_flags: dict[str, Any]
    rollback_snapshot: dict[str, Any]
    merge_audit_id: str | None = None
    error: str | None = None


def _or_flags(keeper: dict, mergee: dict) -> dict[str, Any]:
    """Most-restrictive OR on boolean safety flags (never clear a keeper positive)."""
    out: dict[str, Any] = {}
    for flag in BOOL_FLAGS:
        out[flag] = bool(keeper.get(flag)) or bool(mergee.get(flag))
    return out


def _plan_merge(
    store: Ike2MergeStore,
    *,
    into_group_id: str,
    from_group_id: str,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Return (merged_flags, rollback_snapshot, error)."""
    into = store.get_group(into_group_id)
    frm = store.get_group(from_group_id)
    if into is None:
        return {}, {}, f"into_group_not_found:{into_group_id}"
    if frm is None:
        return {}, {}, f"from_group_not_found:{from_group_id}"
    if into_group_id == from_group_id:
        return {}, {}, "same_group"
    if frm.get("superseded_by"):
        return {}, {}, f"from_already_superseded:{from_group_id}"
    if into.get("superseded_by"):
        return {}, {}, f"into_already_superseded:{into_group_id}"

    merged_flags = _or_flags(into, frm)
    into_ingredients = store.list_ingredients(into_group_id, active_only=True)
    from_ingredients = store.list_ingredients(from_group_id, active_only=True)
    keeper_by_norm = {
        (i.get("normalized_name") or ""): i for i in into_ingredients if i.get("normalized_name")
    }

    aliases_retargeted: list[dict] = []
    ingredients_superseded: list[dict] = []
    ingredients_moved: list[dict] = []

    for ing in from_ingredients:
        norm = ing.get("normalized_name") or ""
        if not norm:
            continue
        keeper = keeper_by_norm.get(norm)
        if keeper is not None:
            for alias in store.list_aliases(ing["id"]):
                aliases_retargeted.append(
                    {
                        "id": alias["id"],
                        "normalized_alias": alias.get("normalized_alias"),
                        "from_ingredient_id": ing["id"],
                        "to_ingredient_id": keeper["id"],
                    }
                )
            ingredients_superseded.append(
                {
                    "id": ing["id"],
                    "normalized_name": norm,
                    "superseded_by": keeper["id"],
                    "prior_group_id": from_group_id,
                }
            )
        else:
            ingredients_moved.append(
                {
                    "id": ing["id"],
                    "normalized_name": norm,
                    "from_group_id": from_group_id,
                    "to_group_id": into_group_id,
                }
            )

    snapshot = {
        "from_group_id": from_group_id,
        "into_group_id": into_group_id,
        "from_group": deepcopy(frm),
        "into_group_before": deepcopy(into),
        "merged_flags": merged_flags,
        "aliases_retargeted": aliases_retargeted,
        "ingredients_superseded": ingredients_superseded,
        "ingredients_moved": ingredients_moved,
    }
    return merged_flags, snapshot, None


def merge_groups(
    store: Ike2MergeStore,
    *,
    into_group_id: str,
    from_group_id: str,
    dry_run: bool = True,
) -> MergeResult:
    """Merge ``from_group_id`` into ``into_group_id``.

    Default ``dry_run=True`` plans + builds ``rollback_snapshot`` without writes.
    On apply: OR flags onto keeper, retarget colliding aliases, move unique
    ingredients, supersede mergee group, insert ``ike2_group_merges`` audit row.
    """
    merged_flags, snapshot, err = _plan_merge(
        store, into_group_id=into_group_id, from_group_id=from_group_id
    )
    if err:
        return MergeResult(
            applied=False,
            dry_run=dry_run,
            into_group_id=into_group_id,
            from_group_id=from_group_id,
            merged_flags={},
            rollback_snapshot={},
            error=err,
        )

    if dry_run:
        return MergeResult(
            applied=False,
            dry_run=True,
            into_group_id=into_group_id,
            from_group_id=from_group_id,
            merged_flags=merged_flags,
            rollback_snapshot=snapshot,
        )

    # Apply
    store.update_group_flags(into_group_id, merged_flags)
    for item in snapshot["aliases_retargeted"]:
        store.retarget_alias(item["id"], item["to_ingredient_id"])
    for item in snapshot["ingredients_superseded"]:
        store.supersede_ingredient(item["id"], item["superseded_by"])
    for item in snapshot["ingredients_moved"]:
        store.reassign_ingredient_group(item["id"], item["to_group_id"])
    store.supersede_group(from_group_id, into_group_id)
    audit_id = store.insert_merge_audit(
        from_group_id=from_group_id,
        into_group_id=into_group_id,
        rollback_snapshot=snapshot,
    )
    return MergeResult(
        applied=True,
        dry_run=False,
        into_group_id=into_group_id,
        from_group_id=from_group_id,
        merged_flags=merged_flags,
        rollback_snapshot=snapshot,
        merge_audit_id=audit_id,
    )
