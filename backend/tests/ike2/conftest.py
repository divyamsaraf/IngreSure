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
