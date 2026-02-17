#!/usr/bin/env python3
"""
Periodic enrichment: fetch unknown ingredients from APIs and add high-confidence
results to dynamic_ontology.json. Run via cron or scheduler.
Usage: cd backend && python scripts/run_enrichment.py [--min-frequency 2] [--dry-run]
"""
import argparse
import logging
import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Enrich unknown ingredients from APIs into dynamic ontology")
    parser.add_argument("--min-frequency", type=int, default=1, help="Min times seen to consider for enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to dynamic ontology")
    args = parser.parse_args()

    from core.enrichment.unknown_log import get_unknown_log
    from core.enrichment.dynamic_ontology import append_to_dynamic_ontology
    from core.external_apis.fetcher import enrich_unknown_ingredient

    log = get_unknown_log()
    keys = log.get_keys_for_enrichment(min_frequency=args.min_frequency)
    entries = log.get_entries()
    if not keys:
        logger.info("No unknown ingredients to enrich")
        return 0

    logger.info("Enriching %d unknown ingredient keys (min_frequency=%s)", len(keys), args.min_frequency)
    added = 0
    for normalized_key in keys:
        raw = (entries.get(normalized_key) or {}).get("raw_inputs") or [normalized_key]
        raw_input = raw[0] if raw else normalized_key
        result = enrich_unknown_ingredient(raw_input, normalized_key, use_cache=True)
        if result.ingredient is None or result.confidence != "high":
            continue
        if not args.dry_run:
            append_to_dynamic_ontology(result.ingredient, result.source, result.confidence)
            added += 1
            logger.info("ENRICHMENT added id=%s source=%s", result.ingredient.id, result.source)
        else:
            logger.info("DRY-RUN would add id=%s source=%s", result.ingredient.id, result.source)
            added += 1
    logger.info("Enrichment run complete: %d added", added)
    return 0


if __name__ == "__main__":
    sys.exit(main())
