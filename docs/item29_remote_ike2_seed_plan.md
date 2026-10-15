# Item 29 — Remote IKE-2 knowledge population plan

**Status:** open (gates any future real deployment to remote Supabase)  
**Does not block:** Item 16 local closure (Prompt 7)  
**Prerequisite done:** IKE-2 schema migrations applied to remote `gcufjqokqqmcuuayaybu` (2026-09-16). Legacy tables unchanged.

## Goal

Populate remote `ike2_*` so a backend pointed at remote has Tier-3 parity suitable for soak — without corrupting legacy `ingredient_*` data already live there (1342 / 1342 / 2641 / 100).

## Current state (post-migration)

| Table | Remote | Local (verified soak DB) |
|-------|-------:|-------------------------:|
| `ike2_ingredient_groups` | 0 | ~1748 |
| `ike2_ingredients` | 0 | ~1748 |
| `ike2_aliases` | 0 | ~6992 |
| `ike2_restriction_rules` | 52 (seeded by migration) | 52 |
| `ike2_unknown_queue` | 0 | 0 |
| `ike2_shadow_diffs` | 0 | (historical soak rows) |

Tier-1 (truth_anchor) and Tier-2 (`data/ontology.json`) ship with the app. Empty Tier-3 means DB-only knowledge is missing — not “everything hedges.”

## Recommended sequence

1. **Baseline snapshot (read-only)**  
   Re-count remote legacy + `ike2_*` tables; record in this file / tracker. Confirm `ike2_restriction_rules == 52`.

2. **Choose population strategy (pick one; do not mix blindly)**  
   - **A. Rebuild from repo artifacts (preferred for reproducibility)**  
     Point a one-off process at remote (commented remote URL + service role), then:  
     - `python scripts/seed_ike2_ontology.py` from `data/ontology.json`  
     - `bulk_inject` for selected `data/layer1_*.json` sources (same order as local bootstrap docs)  
     - Diff counts vs local; sample verdicts for gelatin/vegan, yeast/jain, tempeh/jain  
   - **B. Export/import from local Supabase**  
     `pg_dump`/`COPY` of `ike2_ingredient_groups`, `ike2_ingredients`, `ike2_aliases` (+ disambiguation if any) into remote. Faster parity with local soak DB; less reproducible from git alone.

3. **Do not copy** `ike2_shadow_diffs` soak history to remote (observational noise). Restriction rules already seeded.

4. **Verification gate (Item 29 exit)**  
   - Remote row counts in the same ballpark as local (or documented intentional subset)  
   - Deliberate API + chat batches against a backend with `SUPABASE_URL` = remote  
   - Zero `false_safe_regression` on the corrected metric; fermentation-class sample (koji/miso/tamari/natto/yeast/tempeh) not false-SAFE  
   - Legacy remote counts still 1342 / 1342 / 2641 / 100

5. **Follow-ups (non-blocking)**  
   - Confirm `20260613*` `ingredients.source` CHECK includes `fda_gras` / `fssai` / `nin` before writing those sources on remote  
   - Item 18 dual-queue consolidation still waits on remote enrichment targeting `ike2_unknown_queue`

6. **Pre-pilot audit dependency (with Item 14)**  
   - Provision a **hosted read-only** replica (or least-privilege service role) of remote `ike2_*` for Item 12 nightly Actions  
   - Store `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` as Actions secrets; set `REQUIRE_LIVE_AUDIT=1` when ready so a skipped live audit is red, not green  
   - Route `--fail-on-findings` failures to Slack/email/pager (ops channel TBD)  
   - Without this, the live audit guard remains local-Beat-only (see `docs/item12_audit_hosting.md`)

## Explicit non-goals

- Not required to close Item 16 local  
- Not a reason to reintroduce `ComplianceEngine` or `IKE2_MODE`  
- Not automatic — remote does **not** rebuild itself
