import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"), reason="needs local supabase"
)

from core.knowledge.ike2.stores.db import resolve_alias, disambiguate


def test_yam_resolves_by_region(seed_yam):
    g = resolve_alias("yam", region="IN")
    assert g.canonical_name == "elephant_foot_yam"


def test_yam_no_region_is_ambiguous(seed_yam):
    assert disambiguate("yam", region=None) == "ambiguous"
