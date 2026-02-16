"""
Canonical ingredient registry. Loads from data/ontology.json.
Lookup by exact normalized key only; no substring guessing.
Unknown ingredient -> caller must treat as UNCERTAIN.
"""
from pathlib import Path
from typing import Optional
import json
import logging

from .ingredient_schema import Ingredient
from core.config import get_ontology_path

logger = logging.getLogger(__name__)

# Path from config (backend-relative resolution)
_DEFAULT_ONTOLOGY_PATH = get_ontology_path()


def _normalize_key(text: str) -> str:
    """Deterministic normalization for lookup. No substring logic."""
    return text.lower().strip().replace("*", "").replace(".", "")


class IngredientRegistry:
    """
    O(1) lookup by normalized canonical_name or alias.
    Does NOT perform substring or fuzzy matching.
    """

    def __init__(self, ontology_path: Optional[Path] = None):
        self._path = ontology_path or _DEFAULT_ONTOLOGY_PATH
        self._by_key: dict[str, Ingredient] = {}
        self._version: str = "0"
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            logger.warning("Ontology file not found at %s; registry empty.", self._path)
            return
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        self._version = data.get("ontology_version", "0")
        for item in data.get("ingredients", []):
            ing = Ingredient.from_dict(item)
            keys = [ing.canonical_name] + (ing.aliases or [])
            for k in keys:
                self._by_key[_normalize_key(k)] = ing
        logger.info("Loaded %d ingredient keys from %s", len(self._by_key), self._path)

    def resolve(self, ingredient_str: str) -> Optional[Ingredient]:
        """
        Resolve a raw ingredient string to a canonical Ingredient.
        Returns None if not found (caller must treat as UNCERTAIN).
        No substring or fuzzy matching.
        Logs unknown ingredients for later ontology updates.
        """
        key = _normalize_key(ingredient_str)
        ing = self._by_key.get(key)
        if ing is None and key:
            logger.info("UNKNOWN_INGREDIENT raw=%s normalized_key=%s", ingredient_str, key)
        return ing

    def get_version(self) -> str:
        return self._version

    def __len__(self) -> int:
        return len(self._by_key)
