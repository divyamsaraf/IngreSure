"""Tier-2 file-backed ontology lookup (design §9.3).

Reads the versioned ``data/ontology.json`` bundled with the app -- no live
dependency, zero network. Rows are converted into the same TruthAnchorFact
shape ``seam.to_compliance_input`` already knows how to flatten, via the same
flag-mapping the bulk-injection ETL uses (peanut/tree-nut parsing, alcohol
role derivation, etc.) so Tier-2 flags mean the same thing Tier-1/Tier-3 do.

Indexed by canonical name only (not aliases): alias disambiguation across
regions is Supabase's job (``ike2_alias_disambiguation``), and a local alias
that collides with a genuinely region-ambiguous DB alias must not silently
short-circuit that disambiguation.

Trust: a row missing its canonical name is incomplete and is skipped rather
than indexed half-formed -- it falls through to Tier 3 / Unknown instead of
ever being invented as SAFE (same incomplete-flags policy as Tier 3, see
resolver._is_well_formed_db_row).
"""
from typing import Optional

from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.etl.load_ontology import load_ontology_records
from core.knowledge.ike2.etl.sources import canonical_source, default_knowledge_state
from core.knowledge.ike2.truth_anchor import TruthAnchorFact
from core.normalization.normalizer import normalize_ingredient_key

_SOURCE = canonical_source("ontology")
_DEFAULT_STATE = default_knowledge_state(_SOURCE)

_NON_FLAG_ROW_KEYS = ("canonical_name", "knowledge_state", "primary_source_url", "classification_method")

_INDEX: Optional[dict[str, TruthAnchorFact]] = None


def _row_to_fact(raw: dict) -> Optional[TruthAnchorFact]:
    if not raw.get("canonical_name"):
        return None
    row, _aliases = map_record(raw, _SOURCE, _DEFAULT_STATE)
    if not row.get("canonical_name"):
        return None
    flags = {k: v for k, v in row.items() if k not in _NON_FLAG_ROW_KEYS}
    return TruthAnchorFact(
        canonical_name=row["canonical_name"],
        flags=flags,
        knowledge_state=row.get("knowledge_state", _DEFAULT_STATE),
    )


def _build_index() -> dict[str, TruthAnchorFact]:
    index: dict[str, TruthAnchorFact] = {}
    for raw in load_ontology_records():
        fact = _row_to_fact(raw)
        if fact is None:
            continue
        key = normalize_ingredient_key(raw.get("canonical_name") or "")
        if key:
            index.setdefault(key, fact)
    return index


def _index() -> dict[str, TruthAnchorFact]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def lookup(normalized_key: str) -> Optional[TruthAnchorFact]:
    if not normalized_key:
        return None
    canon = normalize_ingredient_key(normalized_key)
    index = _index()
    return index.get(normalized_key) or index.get(canon)


def reset_cache() -> None:
    """Test-only: force a re-read of ``data/ontology.json`` on next lookup()."""
    global _INDEX
    _INDEX = None
