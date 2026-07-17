"""
Wikidata SPARQL batch queries for Layer 1 ingredient ingestion.

Endpoint: https://query.wikidata.org/sparql (CC0 data)
"""
from __future__ import annotations

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# Re-export headers from runtime API module for User-Agent policy compliance.
from core.external_apis.wikidata_api import WIKIDATA_HEADERS  # noqa: F401

# E-number registry: items with P628 (EU food additive code). GROUP BY keeps LIMIT on
# distinct items (altLabel joins otherwise explode row count).
QUERY_E_NUMBER_ADDITIVES = """
SELECT ?item ?itemLabel ?eNumber ?casNumber ?originLabel
       (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases) WHERE {
  ?item wdt:P628 ?eNumber .
  OPTIONAL { ?item wdt:P231 ?casNumber . }
  OPTIONAL {
    ?item skos:altLabel ?alias .
    FILTER(LANG(?alias) IN ("en", "de", "fr", "es", "hi"))
  }
  OPTIONAL {
    ?item wdt:P117 ?origin .
    ?origin rdfs:label ?originLabel .
    FILTER(LANG(?originLabel) = "en")
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,hi,fr,de,es" . }
}
GROUP BY ?item ?itemLabel ?eNumber ?casNumber ?originLabel
LIMIT 5000
""".strip()

# Food ingredients (Q25403900) plus all E-number items (overlap deduped in transform).
QUERY_FOOD_INGREDIENTS = """
SELECT ?item ?itemLabel ?casNumber ?eNumber
       (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases) WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q25403900 .
  }
  UNION
  {
    ?item wdt:P628 ?eNumber .
  }
  OPTIONAL { ?item wdt:P231 ?casNumber . }
  OPTIONAL {
    ?item skos:altLabel ?alias .
    FILTER(LANG(?alias) IN ("en", "de", "fr", "es", "hi"))
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,hi,fr,de,es" . }
}
GROUP BY ?item ?itemLabel ?casNumber ?eNumber
LIMIT 10000
""".strip()
