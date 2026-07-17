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

from core.normalization.normalizer import normalize_ingredient_key, substance_key, is_e_number_code

logger = logging.getLogger(__name__)

_DEFAULT_ONTOLOGY_PATH = get_ontology_path()
_DEFAULT_DYNAMIC_PATH = get_dynamic_ontology_path()


def _normalize_key(text: str) -> str:
    """Deterministic normalization for lookup. Uses normalize_ingredient_key which applies KNOWN_VARIANTS."""
    return normalize_ingredient_key(text)


def _prefer_substance_entry(existing: Ingredient, new: Ingredient, sk: str) -> Ingredient:
    """When two ontology rows share a substance key, keep the human-readable canonical name."""
    if (existing.canonical_name or "").lower() == sk:
        return existing
    if (new.canonical_name or "").lower() == sk:
        return new
    if is_e_number_code(existing.canonical_name) and not is_e_number_code(new.canonical_name):
        return new
    if is_e_number_code(new.canonical_name) and not is_e_number_code(existing.canonical_name):
        return existing
    return new


def _register_ingredient(by_key: dict[str, Ingredient], ing: Ingredient) -> None:
    """Index ingredient under every alias key; merge with existing substance entries."""
    keys = [ing.canonical_name] + (ing.aliases or [])
    for k in keys:
        nk = _normalize_key(k)
        if not nk:
            continue
        sk = substance_key(nk)
        existing = by_key.get(sk)
        winner = _prefer_substance_entry(existing, ing, sk) if existing else ing
        by_key[nk] = winner
        by_key[sk] = winner


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


def _looks_like_gibberish(key: str) -> bool:
    """
    Reject random keyboard input (e.g. safnaksjnf) before API lookup.
    E-numbers and known short chemical tokens are allowed through.
    """
    if not key or is_e_number_code(key):
        return False
    compact = re.sub(r"[^a-z0-9]", "", key.lower())
    if len(compact) < 8:
        return False
    if not compact.isalpha():
        return False
    vowels = sum(1 for c in compact if c in "aeiou")
    if vowels == 0:
        return True
    # Long alphabetic token with unusual consonant clusters and no dictionary hint
    consonant_run = max(len(m.group()) for m in re.finditer(r"[^aeiouy]+", compact)) if compact else 0
    if len(compact) >= 9 and consonant_run >= 4 and vowels <= 2:
        return True
    return False


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
                _register_ingredient(self._by_key, ing)
                for k in [ing.canonical_name] + (ing.aliases or []):
                    key = _normalize_key(k)
                    if key:
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
                    _register_ingredient(self._by_key, ing)
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
        _register_ingredient(self._by_key, ingredient)

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
        # E-numbers: static ontology only. Never API/dynamic — avoids false Safe from PubChem/ChEBI.
        if is_e_number_code(key):
            sk = substance_key(key)
            for lookup_key in (key, sk):
                if lookup_key in self._static_keys:
                    ing = self._by_key.get(lookup_key)
                    if ing is not None:
                        return ing, "static", "high"
            if log_unknown:
                from core.enrichment.unknown_log import log_unknown_ingredient
                log_unknown_ingredient(
                    ingredient_str, key,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                )
            logger.info(
                "E_NUMBER unknown in static ontology, skipping API raw=%s key=%s",
                ingredient_str[:50], key,
            )
            return None, "static", "low"

        ing, source = self.resolve_with_source(ingredient_str)
        if ing is not None:
            from core.external_apis.enrichment_relevance import is_enrichment_relevant
            if not is_enrichment_relevant(ingredient_str, ing.canonical_name):
                logger.warning(
                    "ENRICHMENT rejected stored species mismatch raw=%s canonical=%s source=%s",
                    ingredient_str[:50], ing.canonical_name[:60], source,
                )
            else:
                return ing, source, "high"

        # Reject obviously non-ingredient strings BEFORE API lookup
        if not _is_valid_ingredient_input(key):
            logger.warning(
                "INGREDIENT_VALIDATION rejected non-ingredient input raw=%s key=%s",
                ingredient_str[:60], key,
            )
            return None, "static", "low"
        if _looks_like_gibberish(key):
            logger.warning(
                "INGREDIENT_VALIDATION rejected gibberish input raw=%s key=%s",
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

        from core.external_apis.enrichment_relevance import is_enrichment_relevant
        canonical = result.ingredient.canonical_name
        if not is_enrichment_relevant(ingredient_str, canonical):
            logger.warning(
                "ENRICHMENT rejected API species mismatch raw=%s canonical=%s source=%s",
                ingredient_str[:50], canonical[:60], result.source,
            )
            return None, "api", "low"
        if result.confidence == "high":
            append_to_dynamic_ontology(result.ingredient, result.source, result.confidence)
            self.add_ingredient(result.ingredient)
            self._by_key[key] = result.ingredient  # so "bajra" resolves next time without re-querying
            logger.info(
                "ONTOLOGY_ENRICHMENT added raw=%s normalized_key=%s canonical_name=%s id=%s source=%s",
                ingredient_str[:50], key, canonical[:60], result.ingredient.id, result.source,
            )
            return result.ingredient, "api", "high"
        if result.confidence == "medium":
            # Auto-expand knowledge base: persist medium-confidence API results so we don't need to re-query
            append_to_dynamic_ontology(result.ingredient, result.source, result.confidence)
            self.add_ingredient(result.ingredient)
            self._by_key[key] = result.ingredient  # so regional name resolves next time
            logger.info(
                "ONTOLOGY_ENRICHMENT added (medium) raw=%s normalized_key=%s canonical_name=%s source=%s",
                ingredient_str[:50], key, canonical[:60], result.source,
            )
            return result.ingredient, "api", "medium"
        return None, "api", "low"

    def get_version(self) -> str:
        return self._version

    def __len__(self) -> int:
        return len(self._by_key)
