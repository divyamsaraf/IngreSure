"""
Log table of unknown ingredients: raw input, normalized key, frequency, profile context.
Used for enrichment process and traceability.
"""
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import get_unknown_ingredients_log_path

logger = logging.getLogger(__name__)

_DEFAULT_PATH = get_unknown_ingredients_log_path()

# Phrases that are profile commands, not ingredients — do not log or upsert as unknown
_PROFILE_PHRASE_KEYS = frozenset({
    "allergens none", "allergen none", "allergies none", "allergy none",
    "no allergies", "no allergens", "allergens clear", "allergens",
})


class UnknownIngredientsLog:
    """
    In-memory log of unknown ingredients with optional persist to JSON.
    Keys by normalized_key; each entry has raw_inputs (list), frequency, last_seen, profile_context.
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _DEFAULT_PATH
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            self._entries = data.get("unknown_ingredients", {})
        except Exception as e:
            logger.warning("Unknown ingredients log load failed: %s", e)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            snapshot = dict(self._entries)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                {"unknown_ingredients": snapshot, "version": "1.0"},
                f,
                indent=2,
            )

    def record(
        self,
        raw_input: str,
        normalized_key: str,
        restriction_ids: Optional[List[str]] = None,
        profile_context: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> None:
        """Record or update an unknown ingredient."""
        if not normalized_key:
            return
        key_normalized = " ".join(normalized_key.lower().strip().split())
        if key_normalized in _PROFILE_PHRASE_KEYS:
            return
        import time
        now = time.time()
        with self._lock:
            if normalized_key not in self._entries:
                self._entries[normalized_key] = {
                    "normalized_key": normalized_key,
                    "raw_inputs": [],
                    "frequency": 0,
                    "first_seen": now,
                    "last_seen": now,
                    "restriction_ids_sample": [],
                    "profile_context_sample": None,
                }
            ent = self._entries[normalized_key]
            if raw_input and raw_input not in ent["raw_inputs"]:
                ent["raw_inputs"] = (ent["raw_inputs"] + [raw_input])[:20]
            ent["frequency"] = ent.get("frequency", 0) + 1
            ent["last_seen"] = now
            freq = ent["frequency"]
            if restriction_ids and ent.get("restriction_ids_sample") is not None:
                sample = list(ent["restriction_ids_sample"])
                for r in restriction_ids[:5]:
                    if r not in sample:
                        sample.append(r)
                ent["restriction_ids_sample"] = sample[:10]
            if profile_context and not ent.get("profile_context_sample"):
                ent["profile_context_sample"] = profile_context
        if persist:
            self._save()
        # Item 33 Prompt 4: discovery goes to ike2_unknown_queue, not legacy
        # unknown_ingredients (nothing drains that table). JSON log above is unchanged.
        try:
            from core.knowledge.ike2.unknown_queue import enqueue_unknown

            enqueue_unknown(normalized_key, raw_input)
        except Exception as e:  # pragma: no cover
            logger.debug("Unknown ingredient queue write skipped: %s", e)
        logger.info(
            "UNKNOWN_INGREDIENT logged raw=%s normalized_key=%s frequency=%s",
            raw_input[:50], normalized_key, freq,
        )

    def get_entries(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._entries)

    def get_keys_for_enrichment(self, min_frequency: int = 1) -> List[str]:
        """Return normalized keys that should be enriched (e.g. by scheduled job)."""
        with self._lock:
            return [
                k for k, v in self._entries.items()
                if v.get("frequency", 0) >= min_frequency
            ]


_default_log: Optional[UnknownIngredientsLog] = None


def get_unknown_log(path: Optional[Path] = None) -> UnknownIngredientsLog:
    global _default_log
    if _default_log is None:
        _default_log = UnknownIngredientsLog(path)
    return _default_log


def log_unknown_ingredient(
    raw_input: str,
    normalized_key: str,
    restriction_ids: Optional[List[str]] = None,
    profile_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience: record to default log."""
    get_unknown_log().record(
        raw_input, normalized_key,
        restriction_ids=restriction_ids,
        profile_context=profile_context,
    )
