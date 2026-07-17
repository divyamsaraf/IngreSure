"""
PubChem PUG REST batch helpers for Layer 1 food-compound ingestion.

Extends pubchem.py (per-item enrichment) with rate-limited bulk CID discovery,
property fetch, and synonym fetch.

Rate limit: 5 requests/second (NCBI policy).
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Iterator

from core.external_apis.http_retry import get_with_retries, post_with_retries

logger = logging.getLogger(__name__)

PUBCHEM_REST_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
RATE_LIMIT_INTERVAL = 0.21  # 5 req/s
BATCH_PROPERTY_SIZE = 200
BATCH_SYNONYM_SIZE = 200

# Primary query from Tier 2 spec (often returns no CIDs; kept for completeness).
PRIMARY_FOOD_QUERY = "food additive"

# Curated word searches; overly broad terms are capped or skipped.
FOOD_ADDITIVE_SEARCH_TERMS = (
    PRIMARY_FOOD_QUERY,
    "preservative",
    "sweetener",
    "emulsifier",
    "thickener",
    "antioxidant",
    "flavoring agent",
    "flavouring agent",
    "flavor enhancer",
    "flavour enhancer",
    "food coloring",
    "food colouring",
    "acidity regulator",
    "anticaking agent",
    "bulking agent",
    "glazing agent",
    "humectant",
    "raising agent",
    "sequestrant",
    "firming agent",
    "foaming agent",
    "gelling agent",
    "carrageenan",
    "xanthan gum",
    "guar gum",
    "locust bean gum",
    "agar",
    "alginate",
    "pectin",
    "lecithin",
    "maltodextrin",
    "aspartame",
    "sucralose",
    "acesulfame",
    "saccharin",
    "stevia",
    "monosodium glutamate",
    "vanillin",
    "caffeine",
    "caramel color",
    "tartrazine",
    "sunset yellow",
    "allura red",
    "carmine",
    "BHT",
    "BHA",
    "TBHQ",
    "propylene glycol",
    "sorbitol",
    "mannitol",
    "citric acid",
    "ascorbic acid",
    "lactic acid",
    "acetic acid",
    "benzoic acid",
    "sorbic acid",
    "natamycin",
    "nisin",
    "cysteine",
    "gelatin",
    "polysorbate",
    "monoglyceride",
    "diglyceride",
    "sodium benzoate",
    "potassium sorbate",
    "inulin",
    "trehalose",
    "tagatose",
    "maltitol",
    "xylitol",
    "erythritol",
    "monk fruit extract",
    "quillaja extract",
)

# Terms that match huge unrelated sets; hard-cap CIDs per query.
_BROAD_TERM_CAP = 100

_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


class PubChemRateLimiter:
    """Enforce minimum interval between PubChem REST calls."""

    def __init__(self, min_interval: float = RATE_LIMIT_INTERVAL) -> None:
        self.min_interval = min_interval
        self._last_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_at = time.monotonic()


_limiter = PubChemRateLimiter()


def _throttled_get(url: str, *, params: dict | None = None, timeout: int = 60) -> dict | None:
    _limiter.wait()
    resp, err = get_with_retries(url, params=params, timeout=timeout)
    if err or resp is None:
        logger.warning("PubChem GET failed: %s", err)
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code == 503:
        time.sleep(2.0)
        _limiter.wait()
        resp, err = get_with_retries(url, params=params, timeout=timeout)
        if err or resp is None or not resp.ok:
            return None
    if not resp.ok:
        logger.debug("PubChem GET %s status=%s", url[:80], resp.status_code)
        return None
    try:
        return resp.json()
    except json.JSONDecodeError:
        return None


def _throttled_post(url: str, *, timeout: int = 120) -> dict | None:
    _limiter.wait()
    resp, err = post_with_retries(url, timeout=timeout)
    if err or resp is None:
        logger.warning("PubChem POST failed: %s", err)
        return None
    if resp.status_code == 503:
        time.sleep(2.0)
        _limiter.wait()
        resp, err = post_with_retries(url, timeout=timeout)
        if err or resp is None or not resp.ok:
            return None
    if not resp.ok:
        logger.debug("PubChem POST %s status=%s", url[:80], resp.status_code)
        return None
    try:
        return resp.json()
    except json.JSONDecodeError:
        return None


def search_cids_by_name_word(query: str, *, max_cids: int | None = None) -> list[int]:
    """GET /compound/name/{query}/cids/JSON?name_type=word"""
    encoded = urllib.parse.quote(query, safe="")
    url = f"{PUBCHEM_REST_BASE}/compound/name/{encoded}/cids/JSON"
    data = _throttled_get(url, params={"name_type": "word"})
    if not data:
        return []
    ids = data.get("IdentifierList", {}).get("CID") or []
    out = [int(x) for x in ids]
    if max_cids is not None:
        return out[:max_cids]
    return out


def search_food_additive_cids(*, per_term_cap: int = 200) -> dict[str, list[int]]:
    """Run primary + curated word searches. Returns {query: [cids]}."""
    results: dict[str, list[int]] = {}
    for term in FOOD_ADDITIVE_SEARCH_TERMS:
        cap = _BROAD_TERM_CAP if term in ("preservative", "antioxidant", "caffeine") else per_term_cap
        cids = search_cids_by_name_word(term, max_cids=cap)
        if cids:
            results[term] = cids
            logger.info("PubChem word search %r -> %d CIDs", term, len(cids))
    return results


def cid_from_cas(cas: str) -> int | None:
    """Resolve a CAS registry number to a PubChem CID."""
    cas = cas.strip()
    if not _CAS_RE.match(cas):
        return None
    encoded = urllib.parse.quote(cas, safe="")
    url = f"{PUBCHEM_REST_BASE}/compound/name/{encoded}/cids/JSON"
    data = _throttled_get(url, timeout=30)
    if not data:
        return None
    ids = data.get("IdentifierList", {}).get("CID") or []
    return int(ids[0]) if ids else None


def collect_cas_from_layer1(paths: list[Path], *, limit: int | None = None) -> list[str]:
    """Extract CAS numbers from existing Layer 1 JSON files."""
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for row in data if isinstance(data, list) else []:
            for alias in row.get("aliases") or []:
                if not isinstance(alias, str):
                    continue
                a = alias.strip()
                if _CAS_RE.match(a) and a not in seen:
                    seen.add(a)
                    out.append(a)
                    if limit and len(out) >= limit:
                        return out
    return out


def cids_from_cas_list(cas_numbers: list[str]) -> dict[str, int]:
    """Resolve CAS → CID for a list of registry numbers."""
    mapping: dict[str, int] = {}
    for cas in cas_numbers:
        cid = cid_from_cas(cas)
        if cid is not None:
            mapping[cas] = cid
    return mapping


def chunk_list(items: list[int], size: int) -> Iterator[list[int]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_properties_batch(cids: list[int]) -> list[dict[str, Any]]:
    """POST /compound/cid/{cids}/property/IUPACName,MolecularFormula,IsomericSMILES/JSON"""
    rows: list[dict[str, Any]] = []
    for batch in chunk_list(cids, BATCH_PROPERTY_SIZE):
        cid_str = ",".join(str(c) for c in batch)
        url = (
            f"{PUBCHEM_REST_BASE}/compound/cid/{cid_str}/property/"
            f"IUPACName,MolecularFormula,IsomericSMILES/JSON"
        )
        data = _throttled_post(url)
        if not data:
            continue
        props = (data.get("PropertyTable") or {}).get("Properties") or []
        rows.extend(props)
    return rows


def fetch_synonyms_batch(cids: list[int]) -> dict[int, list[str]]:
    """GET /compound/cid/{cids}/synonyms/JSON (up to 200 CIDs per call)."""
    out: dict[int, list[str]] = {}
    for batch in chunk_list(cids, BATCH_SYNONYM_SIZE):
        cid_str = ",".join(str(c) for c in batch)
        url = f"{PUBCHEM_REST_BASE}/compound/cid/{cid_str}/synonyms/JSON"
        data = _throttled_get(url, timeout=120)
        if not data:
            continue
        for info in (data.get("InformationList") or {}).get("Information") or []:
            cid = info.get("CID")
            syns = info.get("Synonym") or []
            if cid is not None:
                out[int(cid)] = [str(s) for s in syns if s]
    return out
