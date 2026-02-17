"""
Canonical ingredient registry. Loads from data/ontology.json and optional data/dynamic_ontology.json.
Lookup by exact normalized key only; no substring guessing.
Supports API fallback for unknown ingredients and self-evolving ontology.
"""
from pathlib import Path
from typing import Literal, Optional, Tuple
import json
import re
import logging

from .ingredient_schema import Ingredient
from core.config import get_ontology_path, get_dynamic_ontology_path

logger = logging.getLogger(__name__)

_DEFAULT_ONTOLOGY_PATH = get_ontology_path()
_DEFAULT_DYNAMIC_PATH = get_dynamic_ontology_path()


def _normalize_key(text: str) -> str:
    """Deterministic normalization for lookup. Uses normalize_ingredient_key which applies KNOWN_VARIANTS."""
    from core.normalization.normalizer import normalize_ingredient_key
    return normalize_ingredient_key(text)


# Words that indicate a string is a sentence/question, not an ingredient name
_SENTENCE_VERBS = {"eat", "can", "have", "does", "allow", "permit", "is", "are", "do", "will",
                   "should", "could", "would", "may", "might", "shall", "make", "tell", "check",
                   "know", "find", "safe", "ok", "okay"}
_DIET_WORDS = {"jain", "vegan", "vegetarian", "halal", "kosher", "hindu", "pescatarian",
               "lacto", "ovo", "sikh", "buddhist"}


def _is_valid_ingredient_input(s: str) -> bool:
    """
    Reject strings that are obviously sentences/questions, not ingredient names.
    Prevents API pollution with queries like 'can jain eat onion'.
    Valid ingredients are typically 1-4 words with no verbs.
    """
    if not s or not s.strip():
        return False
    words = s.lower().split()
    # More than 5 words is almost certainly not a single ingredient
    if len(words) > 5:
        return False
    # If it contains sentence verbs + diet words together, it's a question
    has_verb = any(w in _SENTENCE_VERBS for w in words)
    has_diet = any(w in _DIET_WORDS for w in words)
    if has_verb and has_diet:
        return False
    # If more than half the words are verbs/stopwords, reject
    stopword_count = sum(1 for w in words if w in _SENTENCE_VERBS or w in {"i", "my", "me", "a", "the", "for", "to"})
    if len(words) > 2 and stopword_count > len(words) / 2:
        return False
    return True


class IngredientRegistry:
    """
    O(1) lookup by normalized canonical_name or alias.
    Loads static then dynamic ontology. Optional API fallback for unknowns.
    """

    def __init__(
        self,
        ontology_path: Optional[Path] = None,
        dynamic_ontology_path: Optional[Path] = None,
        load_dynamic: bool = True,
    ):
        self._path = ontology_path or _DEFAULT_ONTOLOGY_PATH
        self._dynamic_path = dynamic_ontology_path or _DEFAULT_DYNAMIC_PATH
        self._load_dynamic = load_dynamic
        self._by_key: dict[str, Ingredient] = {}
        self._static_keys: set[str] = set()
        self._version: str = "0"
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            self._version = data.get("ontology_version", "0")
            for item in data.get("ingredients", []):
                ing = Ingredient.from_dict(item)
                keys = [ing.canonical_name] + (ing.aliases or [])
                for k in keys:
                    key = _normalize_key(k)
                    if key:
                        self._by_key[key] = ing
                        self._static_keys.add(key)
            logger.info("Loaded %d ingredient keys from static %s", len(self._by_key), self._path)
        else:
            logger.warning("Ontology file not found at %s; registry empty.", self._path)

        if self._load_dynamic and self._dynamic_path.exists():
            try:
                with open(self._dynamic_path, encoding="utf-8") as f:
                    dyn = json.load(f)
                for item in dyn.get("ingredients", []):
                    d = {k: v for k, v in item.items() if not str(k).startswith("_")}
                    ing = Ingredient.from_dict(d)
                    keys = [ing.canonical_name] + (ing.aliases or [])
                    for k in keys:
                        key = _normalize_key(k)
                        if key:
                            self._by_key[key] = ing
                logger.info("Loaded %d total keys after dynamic ontology", len(self._by_key))
            except Exception as e:
                logger.warning("Dynamic ontology load failed: %s", e)

    def resolve(self, ingredient_str: str) -> Optional[Ingredient]:
        """
        Resolve a raw ingredient string to a canonical Ingredient (static + dynamic only).
        Returns None if not found. Logs unknown for enrichment.
        """
        key = _normalize_key(ingredient_str)
        ing = self._by_key.get(key)
        if ing is None and key:
            logger.info("UNKNOWN_INGREDIENT raw=%s normalized_key=%s", ingredient_str, key)
        return ing

    def resolve_with_source(self, ingredient_str: str) -> Tuple[Optional[Ingredient], Literal["static", "dynamic"]]:
        """Resolve and return (ingredient, "static"|"dynamic")."""
        key = _normalize_key(ingredient_str)
        ing = self._by_key.get(key)
        if ing is None:
            return None, "static"
        source: Literal["static", "dynamic"] = "static" if key in self._static_keys else "dynamic"
        return ing, source

    def add_ingredient(self, ingredient: Ingredient) -> None:
        """Add an ingredient to in-memory registry (e.g. after API enrichment)."""
        keys = [ingredient.canonical_name] + (ingredient.aliases or [])
        for k in keys:
            key = _normalize_key(k)
            if key:
                self._by_key[key] = ingredient

    def resolve_with_fallback(
        self,
        ingredient_str: str,
        try_api: bool = True,
        log_unknown: bool = True,
        restriction_ids: Optional[list] = None,
        profile_context: Optional[dict] = None,
    ) -> Tuple[Optional[Ingredient], Literal["static", "dynamic", "api"], str]:
        """
        Resolve: 1) static 2) dynamic 3) external API if try_api.
        Returns (ingredient, source, confidence_level).
        On high-confidence API result, adds to dynamic ontology and in-memory registry.
        """
        key = _normalize_key(ingredient_str)
        ing, source = self.resolve_with_source(ingredient_str)
        if ing is not None:
            return ing, source, "high"

        # Reject obviously non-ingredient strings BEFORE API lookup
        if not _is_valid_ingredient_input(key):
            logger.warning(
                "INGREDIENT_VALIDATION rejected non-ingredient input raw=%s key=%s",
                ingredient_str[:60], key,
            )
            return None, "static", "low"

        if log_unknown:
            from core.enrichment.unknown_log import log_unknown_ingredient
            log_unknown_ingredient(
                ingredient_str, key,
                restriction_ids=restriction_ids,
                profile_context=profile_context,
            )

        if not try_api:
            return None, "static", "low"

        from core.external_apis.fetcher import enrich_unknown_ingredient
        from core.enrichment.dynamic_ontology import append_to_dynamic_ontology

        result = enrich_unknown_ingredient(ingredient_str, key, use_cache=True)
        if result.ingredient is None:
            logger.info(
                "EXTERNAL_LOOKUP failed raw=%s normalized_key=%s reason=api_no_result",
                ingredient_str[:50], key,
            )
            return None, "api", "low"

        canonical = result.ingredient.canonical_name
        if result.confidence == "high":
            append_to_dynamic_ontology(result.ingredient, result.source, result.confidence)
            self.add_ingredient(result.ingredient)
            logger.info(
                "ONTOLOGY_ENRICHMENT added raw=%s normalized_key=%s canonical_name=%s id=%s source=%s",
                ingredient_str[:50], key, canonical[:60], result.ingredient.id, result.source,
            )
            return result.ingredient, "api", "high"
        if result.confidence == "medium":
            logger.info(
                "EXTERNAL_LOOKUP human_in_the_loop raw=%s canonical_name=%s source=%s (not auto-added)",
                ingredient_str[:50], canonical[:60], result.source,
            )
            # Still use the ingredient for this request but don't auto-add
            return result.ingredient, "api", "medium"
        return None, "api", "low"

    def get_version(self) -> str:
        return self._version

    def __len__(self) -> int:
        return len(self._by_key)
