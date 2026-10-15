"""License gate for new IKE-2 SourceAdapters (Item 1.3 / Prompt 4).

Existing Layer-1 transforms are grandfathered and do **not** call this helper
(strangler-fig). Only ``emit_layer1_records`` / new adapters use it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

_DEFAULT_ALLOWLIST = Path(__file__).resolve().parent / "license_allowlist.json"


@dataclass(frozen=True)
class LicenseDecision:
    allowed: bool
    reason: str

    def __bool__(self) -> bool:
        return self.allowed


def _normalize_spdx(value: str | None) -> str:
    return (value or "").strip()


@lru_cache(maxsize=4)
def _load_allowlist(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.is_file():
        return {"allowed_licenses": [], "source_licenses": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def clear_allowlist_cache() -> None:
    _load_allowlist.cache_clear()


def license_check(
    source_id: str,
    license_spdx: str | None,
    *,
    allowlist_path: Path | None = None,
) -> LicenseDecision:
    """Allow or deny Layer-1 emission for a new adapter source.

    Fail-closed: missing SPDX / unknown license / missing allowlist → deny.
    """
    path = allowlist_path or _DEFAULT_ALLOWLIST
    cfg = _load_allowlist(str(path.resolve()))
    spdx = _normalize_spdx(license_spdx)
    if not spdx:
        return LicenseDecision(False, "missing_license_metadata")

    source_key = (source_id or "").strip().lower()
    per_source: Mapping[str, Any] = cfg.get("source_licenses") or {}
    if source_key in per_source:
        allowed_for_source = {str(x).strip() for x in (per_source.get(source_key) or [])}
        if spdx in allowed_for_source:
            return LicenseDecision(True, "allow_source_license")
        return LicenseDecision(False, f"license_not_allowlisted_for_source:{spdx}")

    global_allowed = {str(x).strip() for x in (cfg.get("allowed_licenses") or [])}
    if spdx in global_allowed:
        return LicenseDecision(True, "allow_global_license")
    return LicenseDecision(False, f"license_not_allowlisted:{spdx}")
