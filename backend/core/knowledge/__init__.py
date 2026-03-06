"""
Knowledge layer scaffolding.

This package will gradually take over:
- canonical ingredient identity resolution
- knowledge state / lifecycle management
- multi-layer caching in front of databases and external APIs

Phase 1 intentionally keeps behavior identical by delegating to existing
ontology + enrichment code paths. Future phases will route resolution
through this package without changing the public decision engine contract.
"""

