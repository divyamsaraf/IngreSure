# backend/core/knowledge/ike2/coverage_os/promote_writer.py
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger

log = logging.getLogger(__name__)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    """Write JSON via temp file + os.replace — never leave half-written target."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _payload(entry: Mapping[str, Any]) -> dict[str, Any]:
    raw = entry.get("payload")
    if not isinstance(raw, dict):
        raise ValueError("promotion entry requires payload dict")
    return dict(raw)


def _managed_alias_set(data: Mapping[str, Any]) -> set[str]:
    """Keys Coverage OS may overwrite/retract. Parallel to aliases string map.

    Keeps ``aliases`` values as bare strings so ``variant_aliases.py`` consumers
    stay unchanged. Marker lives in ``coverage_os_managed_aliases`` (list).
    """
    return {str(x) for x in (data.get("coverage_os_managed_aliases") or [])}


def _apply_variant_alias(payload: Mapping[str, Any], *, aliases_path: Path) -> None:
    alias = str(payload.get("alias") or "").strip()
    canonical = str(payload.get("canonical") or "").strip()
    if not alias or not canonical:
        raise ValueError("variant_alias requires alias and canonical")
    data = _read_json(aliases_path)
    aliases = dict(data.get("aliases") or {})
    managed = _managed_alias_set(data)
    if alias in aliases and alias not in managed:
        raise ValueError(
            f"refusing to overwrite non-coverage_os_managed alias: {alias}"
        )
    aliases[alias] = canonical
    managed.add(alias)
    data["aliases"] = aliases
    data["coverage_os_managed_aliases"] = sorted(managed)
    _atomic_write_json(aliases_path, data)


def _retract_variant_alias(inverse: Mapping[str, Any], *, aliases_path: Path) -> None:
    alias = str(inverse.get("alias") or "").strip()
    if not alias:
        raise ValueError("variant_alias inverse requires alias")
    data = _read_json(aliases_path)
    aliases = dict(data.get("aliases") or {})
    managed = _managed_alias_set(data)
    if alias not in managed:
        if alias not in aliases:
            return  # idempotent: nothing Coverage OS owned
        raise ValueError(
            f"refusing to retract non-coverage_os_managed alias: {alias}"
        )
    aliases.pop(alias, None)
    managed.discard(alias)
    data["aliases"] = aliases
    data["coverage_os_managed_aliases"] = sorted(managed)
    _atomic_write_json(aliases_path, data)


def _apply_ontology_row(payload: Mapping[str, Any], *, ontology_path: Path) -> None:
    name = str(payload.get("canonical_name") or "").strip()
    if not name:
        raise ValueError("ontology_row requires canonical_name")
    flags = dict(payload.get("flags") or {})
    data = _read_json(ontology_path)
    ingredients = list(data.get("ingredients") or [])

    existing_idx = None
    for i, row in enumerate(ingredients):
        if str(row.get("canonical_name") or "").strip() == name:
            existing_idx = i
            break

    if existing_idx is not None:
        existing = ingredients[existing_idx]
        if not existing.get("coverage_os_managed"):
            raise ValueError(
                f"refusing to overwrite non-coverage_os_managed row: {name}"
            )
        row = dict(existing)
    else:
        row = {
            "id": name.replace(" ", "_"),
            "canonical_name": name,
            "aliases": [],
        }

    # Nested flags (test/audit) + flat copies (match data/ontology.json consumers).
    row["flags"] = flags
    for k, v in flags.items():
        row[k] = v
    row["coverage_os_managed"] = True

    if existing_idx is not None:
        ingredients[existing_idx] = row
    else:
        ingredients.append(row)
    data["ingredients"] = ingredients
    _atomic_write_json(ontology_path, data)


def _retract_ontology_row(inverse: Mapping[str, Any], *, ontology_path: Path) -> None:
    name = str(inverse.get("canonical_name") or "").strip()
    if not name:
        raise ValueError("ontology_row inverse requires canonical_name")
    data = _read_json(ontology_path)
    ingredients = list(data.get("ingredients") or [])
    kept: list[dict[str, Any]] = []
    removed = False
    for row in ingredients:
        if str(row.get("canonical_name") or "").strip() != name:
            kept.append(row)
            continue
        # Only reverse what Coverage OS itself added.
        if not row.get("coverage_os_managed"):
            raise ValueError(
                f"refusing to retract non-coverage_os_managed row: {name}"
            )
        removed = True
        # drop row
    if not removed:
        # Idempotent: nothing to remove.
        return
    data["ingredients"] = kept
    _atomic_write_json(ontology_path, data)


def apply_promotion(
    entry: Mapping[str, Any],
    *,
    ontology_path: Path,
    aliases_path: Path,
) -> None:
    payload = _payload(entry)
    kind = payload.get("write_kind")
    if kind == "variant_alias":
        _apply_variant_alias(payload, aliases_path=Path(aliases_path))
        return
    if kind == "ontology_row":
        _apply_ontology_row(payload, ontology_path=Path(ontology_path))
        return
    raise ValueError(f"unsupported write_kind: {kind!r}")


def retract_promotion(
    entry: Mapping[str, Any],
    *,
    ontology_path: Path,
    aliases_path: Path,
) -> None:
    payload = _payload(entry)
    inverse = payload.get("inverse")
    if not isinstance(inverse, dict):
        raise ValueError("retract requires payload.inverse dict")
    kind = inverse.get("write_kind") or payload.get("write_kind")
    if kind == "variant_alias":
        _retract_variant_alias(inverse, aliases_path=Path(aliases_path))
        return
    if kind == "ontology_row":
        _retract_ontology_row(inverse, ontology_path=Path(ontology_path))
        return
    raise ValueError(f"unsupported inverse write_kind: {kind!r}")


def commit_promotion(
    entry: Mapping[str, Any],
    ledger: PromoteLedger,
    *,
    ontology_path: Path,
    aliases_path: Path,
    rule_id: str,
    source: str,
    auto: bool = True,
    reviewer_id: str | None = None,
    approval_rationale: str | None = None,
    candidate_key: str | None = None,
) -> dict[str, Any]:
    """Write L2 first; only then append ledger promoted row.

    If apply_promotion raises, ledger is untouched (pending / no promoted entry).
    """
    apply_promotion(entry, ontology_path=ontology_path, aliases_path=aliases_path)
    key = candidate_key or entry.get("candidate_key")
    if not key:
        raise ValueError("commit_promotion requires candidate_key")
    return ledger.append_promoted(
        candidate_key=str(key),
        rule_id=rule_id,
        source=source,
        payload=_payload(entry),
        auto=auto,
        reviewer_id=reviewer_id,
        approval_rationale=approval_rationale,
    )


def commit_demotion(
    entry: Mapping[str, Any],
    ledger: PromoteLedger,
    *,
    ontology_path: Path,
    aliases_path: Path,
    reason: str,
    candidate_key: str | None = None,
) -> dict[str, Any]:
    """Retract L2 first; only then append ledger demoted row.

    Mirrors ``commit_promotion`` ordering. If retract_promotion raises, ledger
    still shows the prior promotion as active (never claim demote that did not
    hit disk).
    """
    retract_promotion(entry, ontology_path=ontology_path, aliases_path=aliases_path)
    key = candidate_key or entry.get("candidate_key")
    if not key:
        raise ValueError("commit_demotion requires candidate_key")
    return ledger.append_demoted(candidate_key=str(key), reason=reason)


def mirror_l3_inject(entry: Mapping[str, Any]) -> None:
    """Phase 1 stub: L3 is a derived mirror, never source of truth."""
    log.info(
        "coverage_os L3 mirror stub; not source of truth; entry=%s",
        entry.get("candidate_key") or entry.get("kind"),
    )
