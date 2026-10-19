"""Fail CI when a group column is added without refreshing views that expose g.*.

Postgres expands ``g.*`` at CREATE VIEW time; later ALTER TABLE ADD COLUMN does
not update the view (Item 42 provenance hole, ~25 days).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_MIGRATIONS = _REPO / "supabase" / "migrations"

# Views that project ike2_ingredient_groups (join or from).
_GROUP_VIEWS = ("ike2_v_alias_resolution",)

# Columns the resolver / trust / compliance read from group rows.
_RESOLVER_GROUP_COLS = frozenset({
    "source",
    "asserted_flags",
    "uncertainty_flags",
    "classification_method",
    "knowledge_state",
    "canonical_name",
    "animal_origin",
    "plant_origin",
    "dairy_source",
    "egg_source",
    "gluten_source",
    "fish_source",
    "shellfish_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
})


def _migration_files() -> list[Path]:
    return sorted(_MIGRATIONS.glob("*.sql"))


def _stamp(path: Path) -> str:
    return path.name.split("_", 1)[0]


def test_only_known_group_views_in_migrations():
    """Inventory: if a new view over groups appears, this test forces review."""
    found = set()
    for path in _migration_files():
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(
            r"create\s+(?:or\s+replace\s+)?view\s+public\.(\w+)",
            text,
            re.I,
        ):
            name = m.group(1)
            # Window of SQL after the view name — look for groups reference.
            window = text[m.start() : m.start() + 1200]
            if re.search(r"ike2_ingredient_groups", window, re.I):
                found.add(name)
    assert found == set(_GROUP_VIEWS), (
        f"Views over ike2_ingredient_groups changed: {found}. "
        f"Update _GROUP_VIEWS and ensure each is recreated after column adds."
    )


def test_view_recreate_after_every_group_column_add():
    """Last recreate of each group view must be ≥ last ADD COLUMN on groups."""
    add_stamps: list[str] = []
    view_last: dict[str, str] = {}
    add_re = re.compile(
        r"alter\s+table\s+public\.ike2_ingredient_groups\s+add\s+column",
        re.I,
    )
    for path in _migration_files():
        text = path.read_text(encoding="utf-8")
        stamp = _stamp(path)
        if add_re.search(text):
            add_stamps.append(stamp)
        for view in _GROUP_VIEWS:
            if re.search(
                rf"create\s+(?:or\s+replace\s+)?view\s+public\.{view}\b",
                text,
                re.I,
            ):
                view_last[view] = stamp
    assert add_stamps, "expected at least one ADD COLUMN on ike2_ingredient_groups"
    last_add = max(add_stamps)
    for view in _GROUP_VIEWS:
        assert view in view_last, f"no CREATE VIEW for {view}"
        assert view_last[view] >= last_add, (
            f"{view} last recreated at {view_last[view]} but groups gained a "
            f"column at {last_add}. Add a migration that CREATE OR REPLACE VIEW "
            f"{view} so g.* picks up new columns."
        )


def test_latest_alias_view_sql_projects_resolver_columns():
    """Latest view body must use g.* or list every resolver-read column."""
    latest: Path | None = None
    for path in _migration_files():
        if re.search(
            r"create\s+(?:or\s+replace\s+)?view\s+public\.ike2_v_alias_resolution\b",
            path.read_text(encoding="utf-8"),
            re.I,
        ):
            latest = path
    assert latest is not None
    text = latest.read_text(encoding="utf-8")
    # Extract from CREATE VIEW through trailing ';'
    m = re.search(
        r"create\s+(?:or\s+replace\s+)?view\s+public\.ike2_v_alias_resolution\b.*?;",
        text,
        re.I | re.S,
    )
    assert m, "could not extract view DDL"
    body = m.group(0).lower()
    if re.search(r"\bg\.\*", body):
        return
    missing = [c for c in _RESOLVER_GROUP_COLS if c not in body]
    assert not missing, f"alias view omits resolver columns: {missing}"


def test_live_alias_view_exposes_source_and_bulk_uncapped():
    """Live: resolve a bulk alias via the view — source non-null, no firm SAFE."""
    from types import SimpleNamespace

    from dotenv import load_dotenv

    load_dotenv(_REPO / "backend" / ".env")
    from core.knowledge.ingredient_db import get_supabase_config
    from core.knowledge.ike2 import resolution_cache as cache
    from core.knowledge.ike2 import rules as rules_module
    from core.knowledge.ike2.compliance import evaluate
    from core.knowledge.ike2.resolver import resolve
    from core.knowledge.ike2.seam import to_compliance_input
    from core.knowledge.ike2.stores import db
    from core.knowledge.ike2.verdict import to_external

    if not get_supabase_config():
        pytest.skip("Supabase not configured")
    db._client = None
    try:
        row = db.resolve_alias("bread and acesulfame", None)
    except Exception as exc:
        pytest.skip(f"DB unavailable: {exc}")
    if row is None:
        pytest.skip("fixture alias not in local DB")
    assert getattr(row, "source", None), "view must expose source"
    cache.clear()
    r = resolve("bread and acesulfame", None)
    ci = to_compliance_input(r, query_atom="bread and acesulfame")
    assert ci.trusted is False
    v = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"gluten_free": "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )
    assert v != "SAFE"
