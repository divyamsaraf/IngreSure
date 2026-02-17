"""
Dynamic ontology: load from JSON, append validated ingredients from enrichment.
Tracks source and confidence per addition.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import get_dynamic_ontology_path
from core.ontology.ingredient_schema import Ingredient

logger = logging.getLogger(__name__)

_DEFAULT_PATH = get_dynamic_ontology_path()


class DynamicOntology:
    """
    Manages data/dynamic_ontology.json: list of ingredients added by enrichment.
    Each entry can have source (usda_fdc, open_food_facts) and confidence (high, medium).
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _DEFAULT_PATH
        self._ingredients: List[Dict[str, Any]] = []
        self._version: str = "1.0"
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._ingredients = []
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            self._ingredients = data.get("ingredients", [])
            self._version = data.get("ontology_version", "1.0")
            logger.info("Loaded %d ingredients from dynamic ontology %s", len(self._ingredients), self._path)
        except Exception as e:
            logger.warning("Dynamic ontology load failed: %s", e)
            self._ingredients = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "ontology_version": self._version,
                    "ingredients": self._ingredients,
                },
                f,
                indent=2,
            )

    def append(
        self,
        ingredient: Ingredient,
        source: str,
        confidence: str,
        persist: bool = True,
    ) -> None:
        """Add an ingredient from enrichment. Dedupe by id."""
        existing_ids = {ing.get("id") for ing in self._ingredients}
        if ingredient.id in existing_ids:
            logger.debug("Dynamic ontology already has id=%s", ingredient.id)
            return
        entry = ingredient.to_dict()
        entry["_enrichment_source"] = source
        entry["_enrichment_confidence"] = confidence
        self._ingredients.append(entry)
        if persist:
            self._save()
        logger.info(
            "ENRICHMENT added to dynamic ontology id=%s source=%s confidence=%s",
            ingredient.id, source, confidence,
        )

    def get_ingredient_dicts(self) -> List[Dict[str, Any]]:
        """Return list of ingredient dicts (without _enrichment_* for schema compatibility)."""
        out = []
        for ing in self._ingredients:
            d = {k: v for k, v in ing.items() if not k.startswith("_")}
            out.append(d)
        return out

    def get_version(self) -> str:
        return self._version


def load_dynamic_ontology(path: Optional[Path] = None) -> DynamicOntology:
    return DynamicOntology(path)


def append_to_dynamic_ontology(
    ingredient: Ingredient,
    source: str,
    confidence: str,
) -> None:
    """Append one ingredient to default dynamic ontology file."""
    load_dynamic_ontology().append(ingredient, source, confidence)
