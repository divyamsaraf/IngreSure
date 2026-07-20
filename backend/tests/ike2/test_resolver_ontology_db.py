"""IKE-2 resolver against ontology seeded in local Supabase."""
import os

import pytest

from core.knowledge.ike2 import resolver
from core.knowledge.ike2.etl.bulk_inject import SupabaseWriter, inject
from core.knowledge.ike2.etl.load_ontology import load_ontology_records

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL")
    or (
        "127.0.0.1" not in os.getenv("SUPABASE_URL", "")
        and "localhost" not in os.getenv("SUPABASE_URL", "")
    ),
    reason="needs local supabase",
)


@pytest.fixture
def seed_full_ontology(db_admin, tmp_path):
    records = load_ontology_records()
    reject = tmp_path / "rejects.json"
    writer = SupabaseWriter(db_admin, reject_report=str(reject))
    stats = inject(records, "ontology", writer)
    writer.flush()
    assert stats.rejected == 0, writer._rejects
    yield stats


def test_l3_resolves_niacin_trusted(seed_full_ontology):
    resolved = resolver.resolve("niacin", region=None)
    assert resolved.status == "resolved"
    assert resolved.trusted is True
    # Ontology file is Tier-2; L3 seed is fallback. Either trusted layer is fine.
    assert resolved.resolution_layer in (
        "L2_local_ontology",
        "L3_db_alias",
        "L3_db",
    )


def test_bread_label_all_atoms_trusted_after_l3_seed(seed_full_ontology):
    """Phase 2: L3 seed resolves label atoms; no L5 unknown queue."""
    from core.knowledge.ike2.input_layer import parse_atoms
    from core.knowledge.ike2.resolver import resolve
    from tests.test_label_decomposer import BREAD_LABEL

    for atom in parse_atoms(BREAD_LABEL):
        resolved = resolve(atom.name, None)
        assert resolved.status == "resolved", atom.name
        assert resolved.trusted, atom.name
        assert resolved.resolution_layer != "L5_unknown_queue", atom.name
