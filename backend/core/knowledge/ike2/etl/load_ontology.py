"""Load runtime ontology.json records for IKE-2 bulk injection."""
from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DEFAULT_ONTOLOGY = _REPO_ROOT / "data" / "ontology.json"


def default_ontology_path() -> Path:
    return _DEFAULT_ONTOLOGY


def load_ontology_records(path: Path | None = None) -> list[dict]:
    """Return ingredient dicts from ``data/ontology.json`` (bulk-inject shape)."""
    ontology_path = path or default_ontology_path()
    if not ontology_path.is_file():
        raise FileNotFoundError(f"ontology not found: {ontology_path}")
    data = json.loads(ontology_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        items = data
    else:
        items = data.get("ingredients") or data.get("items") or []
    if not items:
        return []
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        canonical = item.get("canonical_name") or item.get("id") or item.get("name")
        if not canonical:
            continue
        rec = dict(item)
        rec["canonical_name"] = canonical
        rec.setdefault("aliases", list(item.get("aliases") or []))
        rec.setdefault("regions", list(item.get("regions") or []))
        out.append(rec)
    return out
