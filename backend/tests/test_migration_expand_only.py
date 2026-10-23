"""New migrations must be expand-only during the same-project flip."""
from pathlib import Path

from scripts.check_migration_expand_only import find_forbidden, lint_new_migrations

_FORBIDDEN = """
ALTER TABLE public.ike2_aliases DROP COLUMN language;
ALTER TABLE public.ike2_aliases RENAME COLUMN region TO market;
ALTER TABLE public.ike2_aliases ALTER COLUMN match_confidence TYPE int;
ALTER TABLE public.ike2_ingredient_groups DISABLE ROW LEVEL SECURITY;
"""

_OK = """
ALTER TABLE public.ike2_aliases ADD COLUMN IF NOT EXISTS language text;
CREATE TABLE IF NOT EXISTS public.ike2_new_thing (id uuid primary key);
CREATE OR REPLACE VIEW public.ike2_v_alias_resolution AS SELECT 1;
"""


def test_forbidden_statements_are_caught():
    hits = find_forbidden(_FORBIDDEN)
    kinds = {h.kind for h in hits}
    assert "DROP" in kinds
    assert "RENAME" in kinds
    assert "ALTER TYPE" in kinds
    assert "DISABLE RLS" in kinds


def test_expand_only_is_clean():
    assert find_forbidden(_OK) == []


def test_shipped_chain_is_allowlisted_or_clean():
    """Historical files may contain DROP; only files after the last shipped version fail."""
    repo = Path(__file__).resolve().parents[2]
    problems = lint_new_migrations(repo / "supabase" / "migrations")
    assert problems == [], problems
