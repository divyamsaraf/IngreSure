# IKE-2 E-Number Truth Anchor and Catalog Verification

**Status:** Implemented  
**Date:** 2026-06-17  
**Parent:** [IKE-2 design](2026-06-16-ike2-design.md)

## Summary

Expands IKE-2 from ~10 hand-picked E-codes to the full **330-entry** [`data/e_number_catalog.json`](../../../data/e_number_catalog.json) via a generated pipeline. Guarantee: **zero false-Safe** (not 100% definitive verdicts on ambiguous additives).

## Architecture

```
e_number_catalog.json
  → verify_e_number_catalog.py (CI gate, cross-source warnings)
  → generate_ike2_e_numbers.py
       ├─ truth_anchor_e_numbers.json (L1, ~1239 alias keys)
       └─ layer1_e_numbers.json (bulk inject)
  → bulk_inject --source e_number_catalog
```

## Tiering (safety-first)

| Tier | Count | `knowledge_state` | `verdict_cap` | Behavior |
|------|-------|-----------------|---------------|----------|
| A | 280 | LOCKED | — | Unambiguous flags; firm verdicts when rules fire |
| B | 50 | AUTO_CLASSIFIED | WARN | `uncertainty_flags` present; diet-relevant clean passes capped at WARN/UNCERTAIN |

Tier B examples: E471 (mono/diglycerides), E322 (lecithin), E910 (L-cysteine).

**Tier B data rule:** rows with `uncertainty_flags` must not carry definite trigger flags that contradict the ambiguity (e.g. `soy_source=true` with “source unspecified”, or `animal_origin=true` with “may be synthetic/plant”). The verify script enforces this as `tier_b_contradiction` errors.

**Compliance overlay:** `_effective_flags` only merges hand-curated `LOCKED` truth-anchor facts when the resolved group is also `LOCKED`. Tier B / `AUTO_CLASSIFIED` catalog rows keep their generated flags (prevents hand `l-cysteine` from overriding E910).

## Key modules

| File | Role |
|------|------|
| `backend/core/knowledge/ike2/e_number_catalog.py` | Shared load, tier, map, anchor build |
| `backend/scripts/verify_e_number_catalog.py` | Validation + cross-ref report |
| `backend/scripts/generate_ike2_e_numbers.py` | Artifact generator |
| `backend/core/knowledge/ike2/truth_anchor.py` | Hand anchors + lazy E-map load |
| `backend/core/knowledge/ike2/etl/adapt_e_number.py` | Bulk inject adapter (`alias_type=e_number`) |
| `backend/core/knowledge/ike2/compliance.py` | `uncertainty_flags` restriction-aware gating |

## Ops

```bash
cd backend
python scripts/verify_e_number_catalog.py --fail-on-error
python scripts/generate_ike2_e_numbers.py
python -m core.knowledge.ike2.etl.bulk_inject ../data/layer1_e_numbers.json --source e_number_catalog --dry-run
```

## Honest limits

- Regional bans (E171 EU) are informational in `uncertainty_flags` only.
- Tier B cannot be promoted to firm-Safe for diet rules without curator review.
- E-codes that collapse via `KNOWN_VARIANTS` (e.g. `e120` → `carmine`) resolve through hand or generated anchors.
- B2B integrators may treat external `UNCERTAIN` stricter than B2C; both share one compliance engine.
- Named forms (e.g. `"soy lecithin"`) may still resolve via hand anchors with definite flags while generic E322 stays ambiguous.

## Golden corpus assertions

[`tests/ike2/golden/corpus.jsonl`](../../../backend/tests/ike2/golden/corpus.jsonl) rows include:

- `expected_verdict` — exact external 3-tier label (`SAFE`, `UNCERTAIN`, `NOT_SAFE`)
- `must_not_be_safe` — hard safety gate (never `SAFE` when true)

Compound terms (`natural flavors`, `spices`) and unknown ingredients expect `UNCERTAIN` (fail-closed, not false-Safe). Hand anchors for compound terms use `verdict_cap=WARN`.

## CI gates

- `verify_e_number_catalog.py --fail-on-error`
- `generate_ike2_e_numbers.py` + zero git diff on generated artifacts
- Full `tests/ike2/` including `test_golden_exact_verdict.py` and `test_pipeline_e2e.py`

## Tests

- `tests/ike2/test_e_number_catalog.py` — all 330 codes, subvariants, artifact drift, verify script
- `tests/ike2/test_golden_exact_verdict.py` — exact labeled outcomes on 61-row corpus
- `tests/ike2/test_golden_safety_budget.py` — zero false-Safe (`must_not_be_safe`)
- `tests/ike2/test_pipeline_e2e.py` — parse → resolve → compliance → B2B/B2C response
- `tests/ike2/test_etl_bulk_inject_e_numbers.py` — layer1 dry inject
- Golden corpus includes E100, E441, E471, E322, E910, etc.
