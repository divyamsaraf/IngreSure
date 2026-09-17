# Bulk Injection Hardening — Design Spec

**Status:** Draft — pending user approval  
**Date:** 2026-06-18  
**Related:** `2026-06-16-ike2-design.md` §9, `data/README.md`, `bulk_inject.py`, universal label pipeline spec

---

## 1. Problem statement

IngreSure has **12+ bulk data sources** (OFF, USDA, Wikidata, ChEBI, FDA GRAS, FoodEx2, PubChem, FSSAI, NIN, IFCT, E-numbers, curated ontology) and **two ingestion paths** that do not share the same safety guarantees. Runtime API enrichment (separate concern) can also pollute knowledge if relevance guards are weak.

**User expectation:** Bulk-load thousands of ingredients from any source, with correct flags/aliases, no silent data loss, no false-SAFE from bad rows, and mechanical CI proof on every PR.

**Verified state (2026-06-18):**

| Check | Result |
|-------|--------|
| IKE-2 `bulk_inject` dry-run on all `layer1_*.json` | 34,551 rows; **165 rejected** (USDA only) |
| ETL unit tests | 12/12 pass |
| `validate_ontology.py` on `ontology.json` | **FAIL** — 40 schema + 22 semantic errors |
| Legacy `ingest_layer1_json.py` | No CHECK mirror; silent skip on missing `canonical_name` |

---

## 2. Goals / non-goals

### Goals

1. **One authoritative bulk path** for IKE-2 L3: `transform → layer1_*.json → bulk_inject → ike2_*`.
2. **Fail-closed at every boundary** — bad rows quarantined with reason; batch never aborts; never silently drop.
3. **Transform-time + inject-time validation** — fix fixable issues upstream; reject unfixable ones downstream.
4. **CI gate** — parametrized dry-run across all layer1 files + ontology validation before seed.
5. **Source registry completeness** — trust tiers and default `knowledge_state` for all 12 sources.
6. **Ontology merge → IKE-2 seed** — `ontology.json` must pass validation before `seed_ike2_ontology.py`.
7. **Universal reject remediation** — any row rejected by **any** source’s `bulk_inject` (or failing layer1 contract) goes through the same offline-first cross-source pipeline; APIs optional last.

### Non-goals

- Staging schema + human review gate (deferred per IKE-2 design §9.1 — direct-to-live is safe given `knowledge_state` caps).
- 100% auto-classification accuracy on crowd sources (OFF/Wikidata stay `DISCOVERED`).
- Replacing runtime API enrichment (handled by pattern-class L guards separately).
- LLM in ETL hot path.

---

## 3. Root cause analysis

### RC-1: Dual ingestion paths (architecture drift)

| Path | Entry | Validation | Target |
|------|-------|------------|--------|
| **A. IKE-2** | `bulk_inject` | CHECK mirror + reconcile | `ike2_*` |
| **B. Legacy** | `ingest_layer1_json.py` | Minimal | `ingredient_groups` / `ingredients` |

**Symptom:** Operators run path B from `data/README.md`; IKE-2 resolver never sees data.  
**Root cause:** Phase 2 docs list both; no deprecation guard.  
**Fix:** Document path A as canonical; add `--ike2` redirect or deprecation warning on path B; CI only gates path A.

### RC-2: USDA transform emits CHECK-invalid rows (165 / 3,613)

**Symptom:** `dairy_implies_animal` (136), `egg_implies_animal` (29) at inject.  
**Root cause:** `transform_usda_fdc_bulk.py` sets `dairy_source`/`egg_source` from text inference but does not set `animal_origin=True`.  
**Fix (classification, not diet policy):** After plant-override and category inference, **enforce implication closure**:  
`dairy_source | egg_source | fish_source | shellfish_source | insect_derived` ⇒ `animal_origin=true`.  
Never set `dairy_source` from implication alone. Plant-named products (coconut milk, almond milk) must pass plant override **before** this step. Re-run transform; dry-run must show 0 rejects.

### RC-3: `ontology.json` fails semantic validation

**Symptom:** carmine/cochineal `insect_derived` without `animal_origin`; alcohol entries with all origin flags false.  
**Root cause:** `merge_all_sources.py` OR-merge does not enforce implication rules; no pre-merge semantic pass.  
**Fix:** (a) Auto-fix pass in merge for known implications; (b) `validate_ontology.py` as CI gate; (c) bulk_inject `adapt.py` already sets `animal_origin` from `insect_derived` — merge should too.

### RC-4: Incomplete source registry

**Symptom:** `fssai`, `nin`, `ifct`, `foodex2`, `pubchem` get tier 0 / `UNCLASSIFIED`.  
**Root cause:** `sources.py` only maps OFF/USDA/FDA/e_number/ontology.  
**Fix:** Extend `_CANONICAL`, `_DEFAULT_STATE`, `reconcile._SOURCE_TIER` with regulatory tier for FSSAI/FDA, curated tier for NIN/IFCT, scientific tier for PubChem/FoodEx2/ChEBI.

### RC-5: No CI gate for layer1 bulk quality

**Symptom:** Only `layer1_e_numbers.json` has automated shape + dry-run test.  
**Root cause:** Tests added incrementally per source, not as a matrix.  
**Fix:** `test_layer1_bulk_inject_dry_run.py` — parametrized over all `data/layer1_*.json` with per-source reject budget (0 except documented exceptions).

### RC-6: Runtime enrichment ≠ bulk (chicken → lamb)

**Symptom:** Wrong canonical in UI from USDA API first-hit.  
**Root cause:** API ranking by shared token "mechanically"; no species guard; persisted to `dynamic_ontology.json`.  
**Fix:** Already shipped (pattern-class L). Bulk path unaffected but **must not conflate** when debugging.

### RC-7: Legacy `nut_source` free-text vs IKE-2 split flags

**Symptom:** layer1 rows carry `nut_source: "peanut"`; IKE-2 needs `peanut_source`/`tree_nut_source`.  
**Root cause:** Dual schema — runtime ontology uses `nut_source`; IKE-2 uses booleans.  
**Fix:** `adapt.py` already maps at inject (fail-closed on unrecognized). Transforms should **prefer** emitting split flags in new layer1 writes (optional Phase 2).

---

## 4. Approaches (recommendation)

### Option A — Harden existing direct-to-live pipeline (recommended)

Extend transforms + source registry + CI gates. Keep `bulk_inject` as single write path. Lowest risk; aligns with IKE-2 design §9.1 safety caps.

**Pros:** Minimal architecture change; 34k+ rows already pass; safety invariants preserved.  
**Cons:** No human review queue; audit trail is JSON reject files not `stg_rejects`.

### Option B — Full staging → review → merge gate

Land all rows in `ike2_staging`, human approves, then promote.

**Pros:** Best auditability for regulatory teams.  
**Cons:** Large scope; PostgREST doesn't expose staging today; blocks automation; overkill while `knowledge_state` caps already prevent false-SAFE.

### Option C — Deprecate IKE-2 bulk; only merge to `ontology.json`

Keep single file ontology; seed IKE-2 from ontology only.

**Pros:** One file to reason about.  
**Cons:** Loses per-source provenance and tiered reconcile; merge already failing validation; doesn't scale to 12 independent refresh cycles.

**Recommendation: Option A** with staged follow-up for Option B audit trail (reject table in Supabase) only if compliance team requires it.

---

## 4.1 Classification vs compliance (do not conflate)

Bulk injection answers **“what is this substance?”** Compliance answers **“can this user eat it?”**

| Layer | Responsibility | Example: cow milk |
|-------|----------------|-------------------|
| **Ontology flags** | `animal_origin`, `dairy_source`, `animal_species`, allergen flags, … | `animal_origin=true`, `dairy_source=true` |
| **Compliance rules** | Match flags to user profile (vegan, halal, Jain, allergies) | Vegan → FAIL; lacto-vegetarian → OK on dairy |

Implication rules (`dairy → animal`) enforce **internal consistency**, not “avoid for everyone.” Diets compose at runtime from `restrictions.json` / IKE-2 `rules.py`.

---

## 4.2 Invalid-row policy (three-way, not ignore vs 100% guess)

| Action | When | Goal |
|--------|------|------|
| **Auto-fix** | Safe, deterministic (implications, plant overrides, insect→animal) | Fix contradictions without guessing |
| **Cross-source enrich** | Still invalid or incomplete after auto-fix | Fill maximum fields from **offline** data already downloaded |
| **API enrich** | Cross-source insufficient **and** row still missing critical fields | Last resort; rate-limited; relevance guards |
| **Quarantine** | Still fails CHECK after all tiers | Fail-closed; never silent drop |
| **Load low-trust** | Enriched but ambiguous | `DISCOVERED` + `uncertainty_flags`; Depends, not Safe |

**Honest target:** not “100% of rows injected with perfect flags.” It is: **zero inconsistent rows in DB**, **zero false-Safe on medical rules**, **unknown → Depends**.

---

## 4.3 Tiered reject remediation (all sources — offline first, APIs optional)

**Scope:** Applies to **every** invalid or incomplete row from **every** bulk source — not USDA-only.  
Sources: OFF, USDA, Wikidata, ChEBI, FDA GRAS, FoodEx2, PubChem, FSSAI, NIN, IFCT, E-numbers, ontology seed, and any future `layer1_*.json`.

**Trigger:** Any row in an `ike2_rejects.json` (per-source inject), aggregated `bulk_inject_all` report, or `validate_layer1.py` failure.

**Today’s baseline:** dry-run shows 165 rejects from USDA only; other sources currently pass CHECK. The remediation module is still **source-agnostic** so when OFF/Wikidata/FSSAI/etc. produce rejects after transform changes, the same T0→T4 pipeline runs without new code paths.

For each rejected row, run remediation in strict order. **Stop as soon as the row passes CHECK and field completeness threshold** — APIs are skipped when not needed.

```
Tier 0  Local auto-fix (implications, plant overrides)     — free, deterministic; same rules for all sources
Tier 1  Cross-layer1 index (all 12 layer1_*.json)         — offline; lookup excludes reject’s own source row only when merging (avoid self-confirming bad data)
Tier 2  Cross-staging / ontology.json / truth anchor L1   — offline, curated
Tier 3  External APIs (source-appropriate: USDA/OFF/Wikidata/…) — ONLY if Tiers 0–2 insufficient; pick API by substance type + gap, not by reject source
Tier 4  Re-validate (validate_rows) → re-inject or quarantine
```

**Why offline-first is best for this system:**

- You already have **~34k rows** across 12 layer1 files — much overlap (same substance in Wikidata + USDA + OFF + FSSAI with different fields).
- **No rate limits**, reproducible CI, auditable merges.
- APIs are noisy (chicken→lamb); offline curated + reconcile is safer.
- **Example (USDA today):** 165 dairy/egg rejects often need **Tier 0 only** (implication fix), not APIs.
- **Example (other sources):** Wikidata reject missing `animal_origin` → Tier 1 match from USDA or FSSAI row; FSSAI prohibited substance → Tier 2 truth anchor; OFF crowd row with dual origin → Tier 0 + reconcile, no API.

**Cross-source merge rules (same as production — all sources):**

- Match by normalized `canonical_name` and alias overlap across **all** layer1 files + ontology (not limited to “USDA helps Wikidata”).
- **Most-restrictive OR** on boolean safety flags (never drop a positive allergen/animal flag).
- Union aliases and regions; dedupe by normalized key.
- Track `merged_from: [source, …]` and `original_source` in remediation report for audit.
- Reconcile tier (all merges): regulatory (FSSAI, FDA) > curated (NIN, IFCT, truth anchor) > USDA > Wikidata > OFF > scientific (ChEBI, PubChem, FoodEx2).

**When APIs are NOT required (any source):**

- Tier 0 auto-fix resolves CHECK violation (implication gaps in USDA, OFF, Wikidata, merge, etc.).
- Another layer1 row or ontology entry provides missing flags (cross-source fill).
- Row is intentionally uncertain (`natural flavors`) — load as DISCOVERED, do not API-guess.
- Remediation report marks `api_skipped: true, reason: "fulfilled_offline"`.

**When APIs ARE required (any source):**

- No offline match for canonical or aliases across **all** indexed sources.
- Offline match exists but critical fields still empty after merge.
- Operator explicitly runs `--with-apis` on remediation job (never default in CI).

**Field completeness threshold (before skipping API):**

Minimum to pass inject: satisfies all CHECK constraints.  
Optional “enriched enough” for re-inject without API:

- Has at least one origin signal (`animal_origin | plant_origin | synthetic`) OR explicit `uncertainty_flags`.
- All implication closures satisfied.
- For meat/dairy rows: `animal_species` present when `animal_origin` and halal-relevant (else remain DISCOVERED).

**Operator flow (all sources):**

```bash
# 1. Inject each source (or bulk_inject_all.sh) → per-source ike2_rejects.json
# 2. One remediation pass over aggregated rejects — source-agnostic
python backend/scripts/remediate_ike2_rejects.py \
  --rejects data/ike2_rejects_aggregated.json \
  --layer1-dir data/ \
  --ontology data/ontology.json
# 3. Optional API tier only if still incomplete
python backend/scripts/remediate_ike2_rejects.py ... --with-apis
```

## 5. Target architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ SOURCES (download scripts)                                       │
│ OFF │ USDA │ Wikidata │ ChEBI │ FDA │ FoodEx2 │ PubChem │       │
│ FSSAI │ NIN │ IFCT │ E-numbers │ manual curated                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ transform_*.py (per-source rules)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ layer1_*.json  — ingest contract:                               │
│   canonical_name (required), aliases[], source, bool flags,     │
│   uncertainty_flags[], regions[], animal_species, alcohol_*     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ validate_layer1.py (NEW — schema + implications)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ bulk_inject (--dry-run | live)                                   │
│   adapt → validate_rows (CHECK mirror) → reconcile → upsert      │
│   reject → ike2_rejects.json                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ (optional second pass)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ remediate_rejects.py (ALL sources — offline-first)               │
│   Input: aggregated rejects from every bulk_inject run           │
│   T0 auto-fix → T1 cross-layer1 index → T2 ontology/truth anchor │
│   → T3 APIs only if still incomplete [--with-apis]               │
│   → re-validate → re-inject or permanent quarantine              │
│   Output: ike2_remediation_report.json (per original_source)     │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
                    ike2_ingredient_groups
                    ike2_ingredients
                    ike2_aliases
                            ▲
                            │ seed_ike2_ontology.py (from ontology.json)
┌───────────────────────────┴─────────────────────────────────────┐
│ merge_all_sources.py → ontology.json (runtime registry)          │
│   validate_ontology.py MUST pass before merge commit               │
└─────────────────────────────────────────────────────────────────┘

RUNTIME (separate): API enrichment → pattern-class L relevance → dynamic_ontology
                     (never bulk_inject; never VERIFIED/LOCKED)
```

---

## 6. Use cases

| ID | Actor | Action | Expected outcome |
|----|-------|--------|------------------|
| UC-1 | DevOps | Download tier-1 data, run transforms | 12 `layer1_*.json` files refreshed |
| UC-2 | DevOps | `bulk_inject --dry-run` all sources | 0 rejects after transform + remediation; stats JSON |
| UC-3 | DevOps | `bulk_inject` live to Supabase | Idempotent upsert; reject report if any |
| UC-4 | CI | PR touches transform or layer1 | Parametrized dry-run tests fail on regression |
| UC-5 | CI | PR touches ontology merge | `validate_ontology.py` exit 0 |
| UC-6 | Operator | Re-run same source after fix | Updates, not duplicates (`updated` count) |
| UC-7 | Operator | Cross-source conflict (any pair) | Most-restrictive wins; `needs_review` flagged |
| UC-8 | Operator | Protected LOCKED e-number row | Lower tier cannot downgrade flags |
| UC-9 | Resolver | Query unknown ingredient | L3 hit from bulk; L5 if missing |
| UC-10 | Safety | DISCOVERED row matches allergen rule | WARN/UNCERTAIN, never SAFE |
| UC-11 | Operator | Remediate aggregated rejects (all sources) | Cross-source offline fill; API only if gaps remain |

---

## 7. Edge cases

| Edge case | Layer | Handling |
|-----------|-------|----------|
| Missing `canonical_name` | Transform | Drop with transform report counter (never reach inject) |
| Empty aliases | Inject | Group still created; canonical alias from name |
| Duplicate alias across groups | Schema | `validate_ontology` / DB unique index → reject or merge proposal |
| `dairy_source` without `animal_origin` | Transform + CHECK | Auto-fix in transform; CHECK rejects if slip through |
| `insect_derived` without `animal_origin` | adapt.py | Auto-set `animal_origin=True` at inject |
| Dual `animal_origin` + `plant_origin` | CHECK | Require `uncertainty_flags`; else quarantine |
| `nut_source` ambiguous text | adapt.py | Both `peanut_source` + `tree_nut_source` (fail-closed) |
| `nut_source: coconut` | adapt.py | Recognized non-trigger; no allergen flags |
| Alcohol with `alcohol_content > 0` | adapt.py | `alcohol_role=ingredient` |
| Fermented, no explicit alcohol | adapt.py | `alcohol_role=fermentation_trace` |
| VERIFIED without `primary_source_url` | CHECK | Reject at inject |
| OFF product named "milk" for coconut query | Runtime L2 | Not bulk — relevance guard |
| USDA "mechanically separated" lamb vs chicken | Runtime L1 | Not bulk — species scoring |
| Bare JSON list (no `source` key) | bulk_inject CLI | Require `--source` flag |
| Wrapped vs list dump shapes | `load_dump()` | Both supported |
| `off_taxonomy` vs `open_food_facts` label | sources.py | Map both → `openfoodfacts` |
| India regional aliases | adapt.py | `regions: ["IN"]` → alias scoped to IN |
| E-number catalog | adapt_e_number.py | LOCKED state; `alias_type=e_number` |
| Protected ontology entry + OFF update | reconcile | Protected state blocks flag downgrade |
| Supabase down | CLI | Exit with clear error; dry-run still works |
| 18k ChEBI rows batch | Performance | Batch in chunks of 500; idempotent re-run |
| USDA reject: dairy without animal | Remediation T0 | Same auto-fix as Wikidata/OFF/merge rejects |
| Wikidata reject: insect without animal | Remediation T0 or T1 | T0 implication; else merge from FSSAI/ontology |
| FSSAI reject: missing region scope | Remediation T1 | Merge regions from NIN/IFCT row |
| OFF reject: dual animal+plant origin | Remediation T0 | Require `uncertainty_flags` or quarantine |
| Reject from source X, match in source Y | Remediation T1 | Merge flags from Y; no API; any X/Y pair |
| Reject fixed by implication only | Remediation T0 | API skipped; all sources |
| No offline match, vague name | Remediation T3 optional | API or quarantine as DISCOVERED |
| Cross-source conflict (any pair) | Reconcile | Most-restrictive flags win |
| Self-merge (only match is same source row) | Remediation T1 | Skip self; fall through to T2/T3 |

---

## 8. Safety invariants (non-negotiable)

These must hold after any bulk injection change:

1. **Nothing bulk-loaded reaches `VERIFIED` or `LOCKED`** except e-number catalog (LOCKED by design).
2. **`DISCOVERED` / `UNCLASSIFIED` never produces SAFE** on allergen/medical rules (IKE-2 compliance caps).
3. **CHECK mirror rejects invalid rows** — never POST to DB without passing `validate_rows`.
4. **Most-restrictive reconcile** — positive safety flags are never silently dropped by lower-tier source.
5. **Reject quarantine** — failed rows appear in reject report with `violated_constraint`.
6. **Idempotent keys** — re-run does not duplicate groups/aliases.
7. **Truth anchor L1** — not replaced by bulk; bulk only feeds L3.

---

## 9. Phased delivery (TDD)

### Phase 0 — Baseline verification (no behavior change)

- [ ] Add `test_layer1_bulk_inject_dry_run.py` (parametrize all layer1 files; document USDA 165 reject baseline).
- [ ] Add CI job step: `pytest tests/ike2/test_layer1_bulk_inject_dry_run.py`.
- [ ] Document canonical path in `data/README.md` (IKE-2 bulk_inject primary; legacy ingest deprecated).

### Phase 1 — Fix root causes in data pipeline (P0)

Per-source **transform** fixes reduce rejects upstream; **remediation (Phase 4b)** handles whatever still fails for **any** source.

- [ ] **TDD:** Test `transform_usda_fdc_bulk` sets `animal_origin=True` when dairy/egg inferred (RC-2).
- [ ] Fix USDA transform; re-generate `layer1_usda_fdc.json`.
- [ ] **TDD:** Shared implication helper used by all transforms that infer dairy/egg/fish/insect flags (not USDA-only).
- [ ] Audit other `transform_*_bulk.py` scripts for same implication gaps; fix + regenerate as needed.
- [ ] **Verify:** dry-run rejects = 0 per source (or documented baseline until remediation pass).
- [ ] **TDD:** Test merge auto-fix: `insect_derived` → `animal_origin`.
- [ ] Fix `merge_all_sources.py` implication pass; fix `ontology.json` semantic errors.
- [ ] **Verify:** `validate_ontology.py` exit 0.

### Phase 2 — Source registry completeness (P1)

- [ ] **TDD:** `test_sources_registry.py` — all layer1 `--source` values have tier + default state.
- [ ] Extend `sources.py` and `reconcile._SOURCE_TIER`.
- [ ] Map: `fssai`→tier 4, `fda`→4, `nin`/`ifct`→3, `foodex2`/`pubchem`/`chebi`→3, `wikidata`→2, `openfoodfacts`→1.

### Phase 3 — Layer1 contract validator (P1)

- [ ] **TDD:** `validate_layer1.py` — required fields, bool types, implication rules.
- [ ] Wire into transform scripts (`--validate` flag) and CI.
- [ ] Reject transform output that fails before writing JSON.

### Phase 4 — Operator tooling (P2)

- [ ] `scripts/bulk_inject_all.sh` — dry-run all sources, aggregate reject report.
- [ ] Deprecation warning on `ingest_layer1_json.py` pointing to `bulk_inject`.
- [ ] Optional: `bulk_inject` `--chunk-size` for large ChEBI loads.

### Phase 4b — Cross-source index + reject remediation (P1, all sources, offline-first)

Single remediation module; **no per-source scripts**. Input = aggregated rejects from every `bulk_inject` run.

- [ ] **TDD:** Build `CrossSourceIndex` from all `layer1_*.json` + `ontology.json` (canonical + alias keys).
- [ ] **TDD:** `remediate_row(reject, *, exclude_self_source=True)` — T0 → T1 → re-validate.
- [ ] **TDD:** Parametrize rejects by `original_source`: USDA dairy (T0), Wikidata gap (T1), FSSAI (T2 anchor), synthetic OFF (T3 or quarantine).
- [ ] **TDD:** Assert `api_skipped=true` when any source fixed offline.
- [ ] `scripts/remediate_ike2_rejects.py` — `--rejects` (single file or glob `ike2_rejects_*.json`); optional `--with-apis`.
- [ ] `bulk_inject_all.sh` aggregates rejects → `data/ike2_rejects_aggregated.json` before remediation.
- [ ] Remediation report per row: `{original_source, violated_constraint, tier_used, merged_from, api_skipped, outcome}`.

### Phase 5 — Audit trail (P2, optional)

- [ ] Supabase table `ike2_ingest_rejects` (if compliance needs DB quarantine vs JSON file).
- [ ] Staging schema exposure — only if human review gate is adopted later.

---

## 10. Testing strategy

| Layer | File | What |
|-------|------|------|
| CHECK mirror | `test_etl_validate.py` | Each constraint has positive + negative case |
| Orchestration | `test_etl_bulk_inject.py` | insert/update/reject/idempotent |
| E-numbers | `test_etl_bulk_inject_e_numbers.py` | 330 rows, LOCKED, alias_type |
| Ontology seed | `test_ontology_seed.py` | staples, insect→animal |
| **NEW** Layer1 matrix | `test_layer1_bulk_inject_dry_run.py` | All sources; max reject count |
| **NEW** Transform | `test_transform_usda_implications.py` | dairy/egg → animal_origin |
| **NEW** Sources | `test_sources_registry.py` | tier + state coverage |
| **NEW** Layer1 schema | `test_validate_layer1.py` | contract enforcement |
| **NEW** Cross-source index | `test_cross_source_index.py` | alias lookup, merge semantics |
| **NEW** Remediation tiers | `test_remediate_rejects.py` | Parametrize by source label; T0/T1 without API; API optional |
| CI ontology | `validate_ontology.py` in workflow | exit 0 on `ontology.json` |
| Integration | `seed_ike2_ontology.py --dry-run` | smoke on real file |

**TDD rule:** Every Phase 1+ change starts with a failing test referencing the root cause ID (RC-*).

---

## 11. Success criteria

- [ ] All `layer1_*.json` dry-run through `bulk_inject` with **0 rejects** after transform + remediation (or documented per-source exception list in test).
- [ ] `remediate_ike2_rejects.py` processes rejects from **any** source with same tier pipeline; CI test covers ≥3 source labels.
- [ ] `validate_ontology.py` returns exit 0 on merged `ontology.json`.
- [ ] `sources.py` covers all 12 source labels used in transforms.
- [ ] CI runs layer1 matrix + ontology validation on every PR touching `data/` or `etl/`.
- [ ] `data/README.md` shows single canonical IKE-2 path.
- [ ] No regression in IKE-2 golden / shadow safety budget (0 false-SAFE).

---

## 12. Resolved: ontology vs per-source inject

**Both**, with clear roles:
- **IKE-2 L3:** per-source `bulk_inject` for scale and provenance.
- **Cross-source index:** shared offline lookup for invalid/incomplete rows from **any** bulk source (same data, no extra download).
- **Runtime registry (`ontology.json`):** merged subset for legacy bridge; must pass validation; seed IKE-2 for staples not in any layer1 file.

---

## 13. Approval
 
After approval, invoke **writing-plans** → `docs/superpowers/plans/2026-06-18-bulk-injection-hardening.md` with bite-sized TDD tasks per Phase 0–4.
