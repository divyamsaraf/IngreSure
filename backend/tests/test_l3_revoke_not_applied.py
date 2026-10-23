"""The anon-revoke SQL must not sit in supabase/migrations/ before the flip."""
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_revoke_sql_is_draft_only():
    applied = list((_REPO / "supabase" / "migrations").glob("*ike2_revoke_anon.sql"))
    draft = _REPO / "supabase" / "migrations_draft" / "20261023120000_ike2_revoke_anon.sql"
    assert applied == [], applied
    assert draft.is_file()
    text = draft.read_text(encoding="utf-8")
    assert "DRAFT ONLY" in text
    assert "enable row level security" in text.lower()
