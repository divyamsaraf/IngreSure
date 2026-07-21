# backend/core/knowledge/ike2/coverage_os/promote_ledger.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def candidate_key(atom: str, target_canonical: str | None) -> str:
    a = (atom or "").strip().lower()
    c = (target_canonical or a).strip().lower()
    return f"{a}=>{c}"


class PromoteLedger:
    """Append-only JSONL promote / demote / confirmed_non_promotable ledger."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _iter_rows(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _next_version(self, candidate_key: str) -> int:
        """Strictly monotonic per candidate_key across every kind."""
        max_v = 0
        for row in self._iter_rows():
            if row.get("candidate_key") != candidate_key:
                continue
            try:
                max_v = max(max_v, int(row.get("version") or 0))
            except (TypeError, ValueError):
                continue
        return max_v + 1

    def _append(self, row: dict[str, Any]) -> dict[str, Any]:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def append_promoted(
        self,
        *,
        candidate_key: str,
        rule_id: str,
        source: str,
        payload: dict[str, Any],
        auto: bool = True,
        reviewer_id: str | None = None,
        approval_rationale: str | None = None,
    ) -> dict[str, Any]:
        # Validate BEFORE any write — rejected call must leave no partial row.
        if not auto:
            if not reviewer_id or not str(approval_rationale or "").strip():
                raise ValueError(
                    "human promote requires reviewer_id and approval_rationale"
                )

        row: dict[str, Any] = {
            "kind": "promoted",
            "candidate_key": candidate_key,
            "rule_id": rule_id,
            "source": source,
            "payload": payload,
            "auto": bool(auto),
            "version": self._next_version(candidate_key),
            "active": True,
        }
        if not auto:
            row["reviewer_id"] = reviewer_id
            row["approval_rationale"] = str(approval_rationale).strip()
        return self._append(row)

    def append_demoted(
        self,
        *,
        candidate_key: str,
        reason: str,
        prior_version: int | None = None,
    ) -> dict[str, Any]:
        # Phase 1 decision: demote with no active promote is allowed (prior_version=None).
        if prior_version is None:
            latest = self.latest_promoted(candidate_key)
            prior_version = int(latest["version"]) if latest else None
        row: dict[str, Any] = {
            "kind": "demoted",
            "candidate_key": candidate_key,
            "reason": reason,
            "prior_version": prior_version,
            "version": self._next_version(candidate_key),
            "active": False,
        }
        return self._append(row)

    def append_non_promotable(
        self,
        *,
        candidate_key: str,
        rule_id: str,
        source: str,
        reason: str,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "kind": "confirmed_non_promotable",
            "candidate_key": candidate_key,
            "rule_id": rule_id,
            "source": source,
            "reason": reason,
            "version": self._next_version(candidate_key),
        }
        return self._append(row)

    def find_non_promotable(self, candidate_key: str) -> dict | None:
        """Latest confirmed_non_promotable for this key, or None."""
        hit: dict | None = None
        for row in self._iter_rows():
            if (
                row.get("candidate_key") == candidate_key
                and row.get("kind") == "confirmed_non_promotable"
            ):
                hit = row
        return hit

    def latest_promoted(self, candidate_key: str) -> dict | None:
        """Forward scan: last promoted for key, cleared by a later demoted."""
        current: dict | None = None
        for row in self._iter_rows():
            if row.get("candidate_key") != candidate_key:
                continue
            kind = row.get("kind")
            if kind == "promoted":
                current = row
            elif kind == "demoted":
                current = None
        return current
