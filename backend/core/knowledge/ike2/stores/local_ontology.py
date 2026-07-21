"""Tier-2 file-backed ontology lookup (design §9.3).

Reads the versioned ``data/ontology.json`` bundled with the app -- no live
dependency, zero network. Rows are converted into the same TruthAnchorFact
shape ``seam.to_compliance_input`` already knows how to flatten, via the same
flag-mapping the bulk-injection ETL uses (peanut/tree-nut parsing, alcohol
role derivation, etc.) so Tier-2 flags mean the same thing Tier-1/Tier-3 do.

Indexed by:
  1. canonical name (wins)
  2. explicit aliases + id
  3. safe auto-heads from dump-style labels (``Broccoli, raw`` → ``broccoli``)

Auto-heads use ``commodity_head.simple_commodity_head`` only — multi-comma
names are never shortened (avoids ``Cabbage, bok choy, raw`` → ``cabbage``).

Trust: a row missing its canonical name is incomplete and is skipped rather
than indexed half-formed -- it falls through to Tier 3 / Unknown instead of
ever being invented as SAFE (same incomplete-flags policy as Tier 3, see
resolver._is_well_formed_db_row).
"""
from typing import Optional

from core.knowledge.ike2.commodity_head import extra_index_keys_for_label
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


def _index_keys_for_label(label: str) -> list[str]:
    """Index both pre-regional and post-regional forms of a label.

    Regional remap runs inside ``normalize_ingredient_key`` by default. If we
    only stored the remapped key, a bare regional name could still miss when
    the English target was never promoted. Storing both closes that gap.
    """
    bare = normalize_ingredient_key(label, apply_regional=False)
    remapped = normalize_ingredient_key(label, apply_regional=True)
    out: list[str] = []
    for k in (bare, remapped):
        if k and k not in out:
            out.append(k)
    return out


def _build_index() -> dict[str, TruthAnchorFact]:
    """Index canonicals first, then aliases/id/auto-heads (setdefault — never overwrite)."""
    index: dict[str, TruthAnchorFact] = {}
    rows: list[tuple[dict, TruthAnchorFact]] = []
    for raw in load_ontology_records():
        fact = _row_to_fact(raw)
        if fact is None:
            continue
        rows.append((raw, fact))

    # Pass 1: canonical names win every key they own.
    for raw, fact in rows:
        for key in _index_keys_for_label(raw.get("canonical_name") or ""):
            index.setdefault(key, fact)

    # Pass 2: aliases + id fill gaps only.
    for raw, fact in rows:
        labels = list(raw.get("aliases") or [])
        if raw.get("id"):
            labels.append(str(raw["id"]))
        for label in labels:
            for key in _index_keys_for_label(label):
                index.setdefault(key, fact)

    # Pass 3: safe dump-style heads (``X, raw`` → ``x``) fill remaining gaps.
    for raw, fact in rows:
        labels = [raw.get("canonical_name") or "", *(raw.get("aliases") or [])]
        for label in labels:
            for key in extra_index_keys_for_label(label):
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
    index = _index()
    for key in _index_keys_for_label(normalized_key):
        hit = index.get(key)
        if hit is not None:
            return hit
    # Last chance inside Tier-2: treat the query itself as a dump-style label.
    from core.knowledge.ike2.commodity_head import simple_commodity_head

    bare = normalize_ingredient_key(normalized_key, apply_regional=False)
    head = simple_commodity_head(bare)
    if head and head != bare:
        return index.get(head)
    return None


def reset_cache() -> None:
    """Test-only: force a re-read of ``data/ontology.json`` on next lookup()."""
    global _INDEX
    _INDEX = None
