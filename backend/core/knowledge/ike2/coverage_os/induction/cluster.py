from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.miss_class import classify_miss_class


@dataclass(frozen=True)
class ClusterItem:
    normalized_key: str
    raw: str
    frequency: int
    miss_class: str


def load_clusters(
    log_path: Path | None = None,
    *,
    entries: Mapping[str, Any] | None = None,
    min_frequency: int = 1,
) -> list[ClusterItem]:
    if entries is None:
        if log_path is None:
            raise ValueError("load_clusters requires log_path or entries")
        data = json.loads(Path(log_path).read_text(encoding="utf-8"))
        entries = data.get("unknown_ingredients") or {}
    out: list[ClusterItem] = []
    for key, ent in entries.items():
        if not isinstance(ent, Mapping):
            continue
        freq = int(ent.get("frequency") or 0)
        if freq < min_frequency:
            continue
        raws = ent.get("raw_inputs") or [key]
        raw = str(raws[0] if raws else key)
        nk = str(ent.get("normalized_key") or key)
        out.append(
            ClusterItem(
                normalized_key=nk,
                raw=raw,
                frequency=freq,
                miss_class=classify_miss_class(raw),
            )
        )
    out.sort(key=lambda c: (-c.frequency, c.normalized_key))
    return out
