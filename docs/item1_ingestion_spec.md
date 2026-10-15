# IngreSure — Build Specification: Item 1
## Multi-source ingestion for IKE-2 (strangler-fig)

**Status:** **Core complete (Prompts 1–7).** P8 (parametrized CI dry-run matrix) and P9 (offline reject remediation) remain optional P2 — not required to close Item 1.  
**Companion files:** `docs/item1_item2_gap_report.md` · `docs/system_state_audit.md` §4 · `docs/superpowers/specs/2026-06-16-ike2-design.md` §9 · `docs/superpowers/specs/2026-06-18-bulk-injection-hardening-design.md` · Item 17 strangler-fig decision · tracker rows 1 / 1.1 / 1.2 / 1.3 / 17

---

## 0. How to use this document

Item 1 is **not** “rebuild ingestion from scratch.” A working IKE-2 bulk spine already exists (`adapt` → `validate` → `reconcile` → `bulk_inject`). This spec closes the **remaining** gaps: complete the source registry, harden CI/remediation around Layer-1 dumps, and add **only new** sources behind a real `SourceAdapter` interface (Items 1.1 / 1.2 / 1.3) without touching the ~10 existing bespoke transforms.

Facts in §1 come from the system-state audit and confirmed code paths — do not re-derive wholesale. Where this document says “identify” or “confirm,” investigate first.

Keep this at `docs/item1_ingestion_spec.md`.

---

## 1. Current state (confirmed — act on this)

### 1.1 What already works

- **Canonical IKE-2 bulk path:** `backend/core/knowledge/ike2/etl/bulk_inject.py`  
  Pipeline per row: source label → `adapt.map_record` (or `adapt_e_number`) → `validate.validate_rows` (CHECK mirror) → `reconcile.reconcile` (most-restrictive) → upsert `ike2_ingredient_groups` / `ike2_ingredients` / `ike2_aliases`. Rejects quarantined to a JSON report; batch continues. Idempotent re-runs.
- **Generic adapter:** `etl/adapt.py` — maps Layer-1 JSON into real group columns; nut_source fail-closed split; alcohol_role derivation; insect/bee → animal_origin; `flag_derive.derive_identity_flags` OR-merge.
- **E-number adapter:** `etl/adapt_e_number.py` — LOCKED catalog path.
- **Source registry (partial):** `etl/sources.py` + `reconcile._SOURCE_TIER`.
- **~12 Layer-1 dumps** under `data/layer1_*.json` with per-source `transform_*` scripts (USDA, OFF, Wikidata, ChEBI, FDA GRAS, FoodEx2, PubChem, FSSAI, NIN, IFCT, e-numbers, ontology seed).
- **Safety cap:** nothing bulk-loaded reaches VERIFIED except e-number LOCKED; crowd sources default DISCOVERED so they cannot drive SAFE (design §9.1).
- **Staging schema exists** (`ike2_staging.ingredient_groups`, `stg_rejects`) but **is not used** by the shipped CLI (direct-to-live + JSON rejects).

### 1.2 What does **not** exist yet

- No `SourceAdapter` Protocol / ABC for bulk sources.
- No produce-catalog adapter (Item **1.1**), no animal-product adapter (Item **1.2**), no license-check gate (Item **1.3**).
- Source registry gaps: `nin`, `ifct`, `foodex2`, `pubchem` missing from `_DEFAULT_STATE` / `_SOURCE_TIER` (unknown → `UNCLASSIFIED` / tier `0`).
- No `validate_layer1.py`, no `remediate_ike2_rejects.py`, no parametrized all-layer1 dry-run CI gate (hardening Phases 3–4b largely unimplemented).
- Legacy dual path still present: `backend/scripts/ingest_layer1_json.py` → legacy tables.
- No Celery Beat cron for bulk refresh (audit §8).
- DB-allowed labels without ingest: `fao`, `indb`, `dbpedia`, `foodb`, `uniprot` (out of scope unless explicitly prioritized).

### 1.3 Item 17 strangler-fig decision (binding)

| Class | Rule |
|-------|------|
| **Existing ~10 bespoke sources** | Stay as-is. Do **not** rewrite USDA/OFF/Wikidata/… transforms to implement `SourceAdapter`. They already feed Layer-1 → `map_record`. |
| **New sources (1.1 / 1.2)** | Must implement a real `SourceAdapter` interface and register in `sources.py` / `_SOURCE_TIER`. |
| **License-check (1.3)** | Gate for adapters/sources whose raw data licenses restrict redistribution or commercial use — runs **before** Layer-1 write / inject. |

---

## 2. Purpose of this component

Make multi-source knowledge loading into `ike2_*` **safe, idempotent, and extensible**: existing sources keep working through the hardened Layer-1 → `bulk_inject` spine; new produce/animal sources plug in via `SourceAdapter`; license policy is enforced before data lands; registry + CI prevent silent trust-tier regressions.

---

## 3. Scope

### In scope

- Document and harden the existing `bulk_inject` spine (registry completeness, CI dry-run matrix, optional offline reject remediation).
- Introduce `SourceAdapter` for **new** sources only.
- Item **1.1** Produce adapter (fresh produce / commodity lists → Layer-1 → inject).
- Item **1.2** Animal-product adapter (species-aware animal foods → Layer-1 → inject).
- Item **1.3** License-check gate used by 1.1/1.2 (and any future adapter).
- Deprecation warning on legacy `ingest_layer1_json.py` pointing operators to `bulk_inject`.
- Tests for every new adapter behavior and registry entry.

### Explicitly out of scope

- Rewriting existing bespoke transforms into `SourceAdapter` (Item 17 forbids this under Item 1).
- Full staging → human-review → merge gate (deferred; knowledge_state caps remain the safety story).
- Runtime API enrichment / pattern-class L guards (separate from bulk).
- Entity merge tooling / compound decomposition (Item 2 / 2.1).
- Dual unknown-queue consolidation (Item 18).
- Wiring Celery Beat for scheduled bulk refresh (optional P2; not required to close 1.1–1.3).
- Ingest for `fao` / `indb` / `dbpedia` / `foodb` / `uniprot` unless separately prioritized.

---

## 4. Target design

### 4.1 Keep the existing spine

```
download / curated JSON
        │
        ▼
transform_*.py  (existing sources — untouched)
        │
        ▼
data/layer1_*.json
        │
        ▼
bulk_inject: adapt → validate_rows → reconcile → upsert ike2_*
        │
        └── rejects → JSON report (optional later: stg_rejects)
```

### 4.2 New-source path (strangler-fig)

```
raw produce / animal / licensed feed
        │
        ▼
license_check (1.3) ──deny──► quarantine + report; no Layer-1 write
        │ allow
        ▼
SourceAdapter.fetch / normalize / to_layer1_records()
        │
        ▼
layer1_<source>.json  →  same bulk_inject spine as above
```

### 4.3 `SourceAdapter` contract (new sources only)

Implement as a `typing.Protocol` (or ABC) under `backend/core/knowledge/ike2/etl/adapters/` (exact module path confirmed in Prompt 1). Minimum surface:

```python
class SourceAdapter(Protocol):
    name: str  # canonical registry key

    def license_ok(self) -> bool:
        """True iff redistribution/use policy allows Layer-1 emission."""
        ...

    def to_layer1_records(self) -> list[dict]:
        """Emit Layer-1 dicts compatible with adapt.map_record (canonical_name, aliases, flags, …)."""
        ...
```

Rules:

- Adapters **must not** write Supabase directly — only emit Layer-1 records (or call a shared helper that writes `layer1_*.json`).
- Default `knowledge_state` and reconcile tier come from `sources.py` / `_SOURCE_TIER`, not hard-coded inside adapters.
- Boolean safety flags follow the same implication closure as `adapt.py` / CHECK mirror (`dairy|egg|fish|shellfish|insect|bee` ⇒ `animal_origin`).
- Produce adapter (1.1): plant-forward commodities; must not invent animal flags; regional aliases allowed.
- Animal adapter (1.2): must set `animal_origin` + species when known; never under-flag allergens for the species class.

### 4.4 License-check (1.3)

- Central helper (e.g. `etl/license_check.py`) consulted by every new adapter before emission.
- Inputs: source id, declared license SPDX / policy tag, optional allowlist config file.
- Outputs: allow | deny(reason). Deny → no Layer-1 file mutation; structured report row.
- Existing transforms are **not** retroactively blocked in v1 of 1.3 (strangler-fig); document that grandfathered sources are assumed previously reviewed.

### 4.5 Registry completeness (existing + new)

Extend `_CANONICAL`, `_DEFAULT_STATE`, and `reconcile._SOURCE_TIER` so every Layer-1 `--source` label used in-repo has an explicit tier + default state. Minimum additions from hardening design:

| Canonical | Default state | Tier (approx.) |
|-----------|---------------|----------------|
| `nin`, `ifct` | `AUTO_CLASSIFIED` | curated (~3) |
| `foodex2`, `pubchem`, `chebi` | `DISCOVERED` or scientific curated per existing chebi | ≥2 |
| `fssai`, `fda` | `AUTO_CLASSIFIED` | 4 (already partially present) |
| `produce_catalog` (1.1) | `AUTO_CLASSIFIED` or `DISCOVERED` — decide in Open Questions | assign explicitly |
| `animal_catalog` (1.2) | same | assign explicitly |

Unknown sources remain `UNCLASSIFIED` / tier `0` (fail-closed).

### 4.6 Hardening follow-through (P2, still Item 1)

Align with `2026-06-18-bulk-injection-hardening-design.md` Option A:

- Parametrized dry-run test over all `data/layer1_*.json`.
- Optional offline reject remediation (T0 implication → T1 cross-layer1 → T2 ontology; APIs never default in CI).
- Document IKE-2 `bulk_inject` as the only supported bulk path in `data/README.md`.

---

## 5. Safety invariants (non-negotiable)

1. Nothing bulk-loaded reaches `VERIFIED`/`LOCKED` except the e-number catalog path.
2. `DISCOVERED` / `UNCLASSIFIED` never produce SAFE on allergen/medical rules (compliance caps — do not weaken).
3. CHECK mirror rejects invalid rows; never POST without `validate_rows`.
4. Most-restrictive reconcile: positive safety flags never silently dropped by a lower tier.
5. Reject quarantine: failed rows appear in a report with `violated_constraint` — never silent drop.
6. Idempotent keys: re-run does not duplicate groups/aliases.
7. New adapters cannot bypass license-check (1.3) or registry registration.
8. Existing bespoke transforms are not “fixed” by large refactors under this item — only registry/CI/docs and true bugs (e.g. implication closure) if Prompt work explicitly includes them.

---

## 6. Sub-items

| ID | Title | Deliverable |
|----|-------|-------------|
| **1** | Spine + registry + operator path | Registry complete; deprecation on legacy ingest; docs; CI dry-run baseline |
| **1.1** | Produce `SourceAdapter` | Adapter + Layer-1 emit + inject dry-run green + tests |
| **1.2** | Animal `SourceAdapter` | Same, with species / animal_origin invariants |
| **1.3** | License-check | Shared gate + config + deny-path tests; wired into 1.1/1.2 |

Item **17** is the architectural decision already taken; implementation of the adapter interface lives under Item 1 prompts below.

---

## 7. Numbered build prompts for Cursor

**Prompt 1** — Investigate and report (no behavior change): list every `--source` / dump label currently used by Layer-1 transforms and `bulk_inject`; diff against `sources._CANONICAL`, `_DEFAULT_STATE`, and `reconcile._SOURCE_TIER`. Report missing keys and current fall-through behavior. Confirm there is still no `SourceAdapter` type anywhere under `ike2/etl/`. Do not proceed to Prompt 2 until this inventory is written into this file’s stage log or a short findings subsection.

**Prompt 2** — Registry + trust-gate + provenance (one checkpoint): (a) complete `_DEFAULT_STATE` / `_SOURCE_TIER` for all existing Layer-1 labels including `e_number_catalog`; (b) hard-reject non–e-number bulk rows declaring LOCKED/VERIFIED (`bulk_locked_verified_requires_e_number_catalog`); (c) add `ike2_ingredient_groups.source` so `_PROTECTED_STATES` can engage; tests for LOCKED survival vs most-restrictive OR on non-locked rows. Do **not** invent VERIFIED defaults for bulk sources.

**Prompt 3** — Introduce `SourceAdapter` Protocol (or ABC) + package layout under `ike2/etl/adapters/`. Add a no-op / fake adapter test that proves: license deny → zero records; license allow → records pass `validate_rows` shape expectations. Do **not** refactor USDA/OFF/etc.

**Prompt 4** — Implement Item **1.3** `license_check` helper + config allowlist. Wire it so new adapters must call it before emitting Layer-1. Tests: allow, deny, missing license metadata → deny (fail-closed).

**Prompt 5** — Implement Item **1.1** produce adapter against a small curated seed (path confirmed in investigation — do not scrape licensed sources without 1.3 allow). Emit `layer1_produce_*.json` (or agreed name), register source, dry-run `bulk_inject`, assert 0 CHECK rejects on the seed.

**Prompt 6** — Implement Item **1.2** animal adapter similarly. Invariants: `animal_origin=True` when species/meat/dairy/egg/fish flags set; `animal_species` populated when known; dry-run inject green on seed.

**Prompt 7** — Operator hygiene: add deprecation warning to `ingest_layer1_json.py`; update `data/README.md` to declare IKE-2 `bulk_inject` as the canonical bulk path; optional `scripts/bulk_inject_all.sh` dry-run aggregator if not already present.

**Prompt 8** — (P2) Add parametrized `test_layer1_bulk_inject_dry_run.py` over all `data/layer1_*.json` with per-source reject budgets. Fix only implication-closure bugs required to meet documented budgets — do not broad-refactor transforms.

**Prompt 9** — (P2, optional) Offline `remediate_ike2_rejects.py` T0→T1→T2 per hardening design; CI must not enable `--with-apis`.

---

## 8. Keeping this file in sync

Update the stage log when Prompts 1–7 land. Tracker Item 1 / 1.1 / 1.2 / 1.3 Notes columns should point here — do not recreate obsolete phase docs.

### Stage log

| When | Stage | Notes |
|------|-------|-------|
| 2026-09-17 | **draft** | Spec reconstructed from audit + design §9 + hardening + Item 17 strangler-fig. Implementation not started under this file. |
| 2026-09-18 | **Prompt 1 done** | Inventory below. **No SourceAdapter**. Gaps: nin/ifct/foodex2/pubchem + `e_number_catalog` missing from `_SOURCE_TIER`. Also: dead `_PROTECTED_STATES` (no group `source` column); dump-supplied LOCKED/VERIFIED honored by `adapt`. Ready for Prompt 2 with those caveats scoped. |
| 2026-09-18 | **adapt/LOCKED exposure scan** | Local DB: **0** LOCKED/VERIFIED groups (1738 all `bulk:ontology`; 1730 AUTO / 8 DISCOVERED). No e-number inject present. Coverage OS does not write `ike2_*`. Hole is latent, not live — still fix at root before Prompt 2 (Item-34 shape). See § Prompt 1b. |
| 2026-09-19 | **Prompt 2 done** | Registry: nin/ifct/foodex2/pubchem + `e_number_catalog` tier. Validate hard-reject non–e-number LOCKED/VERIFIED. Migration `20260919000000_ike2_group_provenance_source.sql` (`source` on groups + backfill from `bulk:*`). Reconcile/adapt/bulk_inject write provenance. Tests: sources, validate, reconcile both directions, adapt. |
| 2026-09-21 | **Prompt 3 done** | `ike2/etl/adapters/` — `SourceAdapter` Protocol + `emit_layer1_records` (license deny → `[]`). Fake-adapter tests: deny/allow + `validate_rows`. No USDA/OFF refactor. |
| 2026-09-21 | **Prompt 4 done** | `etl/license_check.py` + `license_allowlist.json` (fail-closed). `emit_layer1_records` dual-gate: central SPDX allowlist then `adapter.license_ok()`. Tests: allow / deny / missing metadata / source-specific override; FakeAdapter missing/disallowed SPDX → `[]`. |
| 2026-09-21 | **Prompt 5 done** | `ProduceCatalogAdapter` + curated CC0 seed (`adapters/seeds/produce_catalog_seed.json`) → `data/layer1_produce_catalog.json`. Registry: `produce_catalog` → `AUTO_CLASSIFIED`, tier 3. Dry-run inject 0 rejects; plant-forward invariants. **Decision (accepted):** curated produce seed = `AUTO_CLASSIFIED` (not DISCOVERED). **Does not carry to `animal_catalog`** — Item 1.2 / Prompt 6 requires its own explicit KS check-in (allergens / kosher-halal / veg* hinge on animal-origin accuracy). `animal_catalog` left unregistered until that check-in. |
| 2026-09-22 | **animal_catalog KS check-in** | **Decision:** `animal_catalog` → `DISCOVERED`, tier **2** (not produce's AUTO/3). Rationale: Item 34 — positive hazard flags still FAIL regardless of KS; DISCOVERED only blocks firm SAFE from unreviewed absence of hazard. Correct asymmetry for animal-origin data. Tier 2 matches other DISCOVERED sources (foodex2, pubchem). Registered in `_DEFAULT_STATE` / `_SOURCE_TIER`; Prompt 6 unblocked. |
| 2026-09-22 | **Prompt 6 done** | `AnimalCatalogAdapter` + CC0 seed → `data/layer1_animal_catalog.json`. Invariants: `animal_origin` when dairy/egg/fish/shellfish/bee set; `animal_species` when known; inject dry-run 0 rejects; rows land `DISCOVERED`. |
| 2026-09-22 | **Prompt 7 done** | `ingest_layer1_json.py` DeprecationWarning + stderr WARNING; `data/README.md` declares IKE-2 `bulk_inject` canonical; `scripts/bulk_inject_all.sh` dry-run aggregator. |
| 2026-09-22 | **core complete** | Prompts 1–7 close Item 1 P0/P1. **P8/P9 deferred** (explicitly optional/P2 in §7). Produce=`AUTO_CLASSIFIED`/t3; animal=`DISCOVERED`/t2. |

### Prompt 1 findings (2026-09-18)

#### Layer-1 dumps in repo (`data/layer1_*.json`)

| Dump file | Sample `source` on rows | Transform script |
|-----------|-------------------------|------------------|
| `layer1_chebi.json` | `chebi` | `transform_chebi_bulk.py` |
| `layer1_usda_fdc.json` | `usda_fdc` | `transform_usda_fdc_bulk.py` |
| `layer1_fda_gras.json` | `fda_gras` | `transform_fda_gras_bulk.py` |
| `layer1_fssai.json` | `fssai` | `transform_fssai_bulk.py` |
| `layer1_wikidata.json` | `wikidata` | `transform_wikidata_batch.py` |
| `layer1_off_taxonomy.json` | `open_food_facts` | `transform_off_taxonomy.py` |
| `layer1_nin.json` | `nin` | `transform_nin_bulk.py` |
| `layer1_ifct.json` | `ifct` | `transform_ifct_bulk.py` |
| `layer1_foodex2.json` | `foodex2` | `transform_foodex2_bulk.py` |
| `layer1_pubchem.json` | `pubchem` | `transform_pubchem_batch.py` |
| `layer1_e_numbers.json` | *(none on rows — CLI `--source`)* | catalog / e-number path |
| `layer1_seed.example.json` | `usda_fdc` | example only |

`bulk_inject.py` takes `--source` (overrides dump; required for bare-list dumps) and runs `canonical_source` → `default_knowledge_state`.

#### Registry diff

| Label / canonical | `_CANONICAL` | `_DEFAULT_STATE` | `_SOURCE_TIER` |
|-------------------|--------------|------------------|----------------|
| `open_food_facts` → `openfoodfacts` | yes | yes (`DISCOVERED`) | yes (1) |
| `usda_fdc` → `usda` | yes | yes (`AUTO_CLASSIFIED`) | yes (3) |
| `fda_gras` → `fda` | yes | yes | yes (4) |
| `fssai` | identity | yes | yes (4) |
| `chebi` | identity | yes | yes (3) |
| `wikidata` | identity | yes | yes (2) |
| `ontology` / `system` | yes | yes | yes (4) |
| `e_number_catalog` | yes | yes (`LOCKED`) | **MISSING** (tier falls to **0**) |
| `nin` | — | **MISSING** → `UNCLASSIFIED` | **MISSING** → tier 0 |
| `ifct` | — | **MISSING** → `UNCLASSIFIED` | **MISSING** → tier 0 |
| `foodex2` | — | **MISSING** → `UNCLASSIFIED` | **MISSING** → tier 0 |
| `pubchem` | — | **MISSING** → `UNCLASSIFIED` | **MISSING** → tier 0 |

Also present in registries but **no Layer-1 dump**: `regulatory`, `human` (tier-only).

#### Fall-through behavior

- `canonical_source`: unknown label → lowercase identity (`_CANONICAL.get(key, key)`).
- `default_knowledge_state`: unknown canonical → **`UNCLASSIFIED`** (most conservative).
- `_tier` / reconcile: unknown source → **tier 0** (loses to any registered source).

#### SourceAdapter

**Confirmed absent** — no `SourceAdapter` / Adapter Protocol/ABC under `backend/core/knowledge/ike2/etl/` (or broader backend search). Spec §1.2 still accurate; Prompt 3 still greenfield for the interface.

#### Surprises vs §1.2

- Spec listed nin/ifct/foodex2/pubchem as registry gaps — **confirmed** (dry-run: all land `UNCLASSIFIED`, 0 CHECK rejects). Utility hit (~2.1k rows never SAFE; tier 0 loses every reconcile), not a false-SAFE hazard today (SAFE floor still caps `UNCLASSIFIED`).
- **Extra registry gap:** `e_number_catalog` has default state `LOCKED` but is **missing from `_SOURCE_TIER`** → reconcile tier **0**.
- **All dumps are bare JSON lists** — `load_dump` returns `source=None`; CLI `--source` is mandatory. Per-row `"source"` on records is **ignored** by `bulk_inject` (legacy ingest only); a mismatched `--source` silently mislabels the batch.
- **`_PROTECTED_STATES` is dead on the live path:** `ike2_ingredient_groups` has **no `source` column**, so `reconcile` always sees `existing_source=""` → tier 0 → protection never engages. A `LOCKED` group can be demoted by a low-tier incoming row today. Registry tier fill alone does not restore protection — schema/write-path work is needed (track for Prompt 2+; may outscope pure registry fill).
- **`adapt.map_record` honors dump-supplied `LOCKED`/`VERIFIED`:** registry default is only a fallback. E-numbers get `LOCKED` from the dump, not `_DEFAULT_STATE`. Other dumps omit `knowledge_state` today, so the “nothing bulk → VERIFIED” cap holds by convention only — Prompt 2 should add an explicit guard/test.

### Prompt 1b — LOCKED/VERIFIED exposure + `_PROTECTED_STATES` (2026-09-18)

#### 1. Exposure (local `ike2_ingredient_groups`)

| Query | Count |
|-------|-------|
| `knowledge_state IN (LOCKED, VERIFIED)` | **0** |
| Of those, non–e-number / non–Coverage-OS | **0** (vacuous) |

Full DB: **1738** groups — all `classification_method=bulk:ontology`; **1730** `AUTO_CLASSIFIED`, **8** `DISCOVERED`. No e-number catalog inject in this environment. `ike2_ingredients` has `source` but **no** `knowledge_state` (trust lives on groups). Coverage OS promotions write L2 files only — never `ike2_*`.

**Verdict:** not live today. Same shape as pre-hit Item 34 — hole exists in code; nothing has walked through it on this DB.

#### 2. What `_PROTECTED_STATES` was for vs most-restrictive-wins

| Mechanism | Protects against | Does **not** protect |
|-----------|------------------|----------------------|
| **Most-restrictive OR** (`existing \|\| incoming`) | Silently **dropping** a positive safety flag | New positives being OR’d on; **KS demotion** |
| **`_PROTECTED_STATES`** (VERIFIED/LOCKED + incoming tier &lt; existing source tier) | Lower tier changing **any** flag (freeze to existing); keeps KS | Equal/higher tier updates |

On a flag conflict with `needs_review`, reconcile sets `knowledge_state = "DISCOVERED"` — so an unprotected LOCKED row that gains any new positive flag is **demoted**.

**Live path:** groups have **no `source` attribute** → `existing_source=""` → `_tier("")==0` → `protected` requires `_tier(incoming) < 0` → **never true**. Confirmed:

- LOCKED without `source` + OFF adds `gluten_source` → flags updated, **`knowledge_state → DISCOVERED`**
- LOCKED with `source="human"` (test shape) + same OFF row → flags frozen, **KS stays LOCKED**

So most-restrictive-wins is **not** equivalent protection for LOCKED/VERIFIED. Positive flags stick; trust rank does not.

#### 3. Cadence recommendation

**Exposure = 0 → not same-day Item-34 urgency**, but **fix at root before Item 1 Prompt 2 registry work**: hard-reject (not silent downgrade) non–e-number dumps claiming LOCKED/VERIFIED in `adapt`; restore or replace `_PROTECTED_STATES` with a real provenance field / documented substitute. Do not treat “registry fill” as closing this.

---

## 9. Success criteria

- [ ] Every in-repo Layer-1 source label has explicit registry tier + default `knowledge_state`.
- [ ] `SourceAdapter` exists and is used by produce + animal adapters only.
- [ ] License-check denies unlicensed new sources before Layer-1 write.
- [ ] Produce + animal seed dry-runs inject with 0 CHECK violations.
- [ ] Existing bespoke transforms unchanged except registry/CI/documented bugfixes.
- [ ] Legacy Layer-1 ingest warns and docs point to `bulk_inject`.
- [ ] No regression in IKE-2 golden / must-never-be-safe fungal/tempeh cases (Item 2 owns decomposition; Item 1 must not strip `fungal`/`fermented` in new animal/produce rows).
