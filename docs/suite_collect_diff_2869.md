# Suite collect-only reconciliation (2869 baseline)

**Date:** 2026-10-15

## Finding

There is **no git commit** at 2869 tests. That figure is the local working-tree
count recorded in [`item42_verification.md`](item42_verification.md) after the
trust-ceiling / asserted-clear follow-up, before this work was committed.

| Snapshot | Collected | Notes |
|----------|-----------|-------|
| Documented local baseline | 2869 passed + 4 skipped | never committed |
| Committed `HEAD` before this PR (`5b64548`) | **1684** | missing all Item 37–44 tests/data |
| Working tree after hardening (pre-splitter) | **2828** (2824 passed + 4 skipped) | this PR |

So 2824 vs 2869 (−45) is a **local → local** delta, not a git regression from
a 2869 commit. Redis deletion (Item 33) explains only 3 of the removed nodeids
vs committed HEAD.

## Collect-only: committed `5b64548` → working tree

```
added since HEAD:   1156
removed since HEAD:   12
```

### Removed nodeids (and why)

| Test ID | Why removed |
|---------|-------------|
| `tests/test_redis_resolution_cache.py::test_redis_cache_round_trip_with_mock` | Redis resolve cache deleted (Item 33; file removed in this PR) |
| `tests/test_redis_resolution_cache.py::test_resolution_cache_unavailable_when_no_redis_url` | same |
| `tests/test_redis_resolution_cache.py::test_resolver_unchanged_without_redis` | same |
| `tests/test_chat_ingredients.py::test_emit_resolution_metric_skips_without_running_event_loop` | metric path retired with canonicalizer |
| `tests/ike2/test_e_number_catalog.py::test_verify_script_zero_errors` | renamed → `test_verify_script_flags_animal_origin_with_non_animal_source` (E626/E630/E631 debt) |
| `tests/ike2/test_compliance.py::test_untrusted_trace_is_uncertain_not_avoid` | replaced by trust-ceiling / fail-stands cases |
| `tests/ike2/test_safety_invariants.py::test_untrusted_never_safe_or_fail` | superseded by source-ceiling invariants |
| `tests/ike2/test_safety_invariants.py::test_untrusted_peanut_true_is_uncertain_not_fail` | same (allergy FAIL stands; untrusted peanut is FAIL) |
| `tests/ike2/test_etl_reconcile.py::test_conflict_takes_most_restrictive_and_flags_review` | replaced by asserted-flag reconcile tests |
| `tests/ike2/test_etl_reconcile.py::test_lower_tier_cannot_override_verified` | same |
| `tests/ike2/test_tier_flag_overlay.py::test_discovered_ks_still_blocks_when_no_tier1` | overlay policy rewritten with trust ceiling |
| `tests/ike2/test_truth_anchor.py::test_animal_derived_additive_keys[l-cysteine]` | cysteine keys moved to dedicated `test_cysteine_labels` |

### Remaining ~41 gap (2869 → 2828)

Without a frozen collect dump from the 2869 run, exact IDs cannot be
recovered. Likely sources of the residual drop:

- Golden / never-SAFE / label-corpus parametrize shrinkage after lactate→Tier B
  and asserted-clear freezes
- Probe/ops tests that were collected once then deleted from the tree before
  this commit
- Collection filters (`-k`, import skips) that differed between runs

**Action:** treat **2828 collected / 2824 passed / 4 skipped** as the new
committed baseline after this PR merges. Re-baseline any tracker that still
cites 2869.

## Alcohol assertion

Recorded in [`item42_trust_by_source_followup.md`](item42_trust_by_source_followup.md)
(FAIL → UNCERTAIN for lifestyle alcohol on untrusted USDA bulk).
