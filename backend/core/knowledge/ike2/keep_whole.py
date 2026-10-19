"""Keep-whole / anti-recipe registry (Item 2 Prompt 4).

Central denylist of process foods that must not be recipe-expanded into
compositional members (tempeh precedent). Loaded from ``data/ike2_keep_whole.json``.

Neutralize ``process_keep`` roles and truth-anchor Tier-1 keep remain separate
mechanisms; this registry owns the ``PROCESSED_FOOD_TO_BASE`` denylist and the
process-identity token set used by ``expand_compounds``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_DEFAULT_PATH = _REPO / "data" / "ike2_keep_whole.json"


def clear_keep_whole_cache() -> None:
    load_keep_whole_names.cache_clear()


@lru_cache(maxsize=8)
def load_keep_whole_names(path_str: str | None = None) -> frozenset[str]:
    if path_str:
        path = Path(path_str)
    else:
        # Resolve module attr at call time so monkeypatch of _DEFAULT_PATH works.
        path = _DEFAULT_PATH
        # Import-cycle-safe: read from this module's global after possible patch.
        import core.knowledge.ike2.keep_whole as mod

        path = mod._DEFAULT_PATH
    if not path.is_file():
        return frozenset()
    data = json.loads(path.read_text(encoding="utf-8"))
    names = data.get("keep_whole") or []
    return frozenset(str(n).strip().lower() for n in names if str(n).strip())


def is_keep_whole(name: str, *, path: Path | None = None) -> bool:
    key = (name or "").strip().lower()
    if not key:
        return False
    if path is not None:
        return key in load_keep_whole_names(str(path.resolve()))
    import core.knowledge.ike2.keep_whole as mod

    return key in load_keep_whole_names(str(mod._DEFAULT_PATH.resolve()))
