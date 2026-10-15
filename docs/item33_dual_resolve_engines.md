# IngreSure — Build Specification: Item 33
## Dual resolve engines → single IKE-2 spine

**Status:** Core complete (Prompts **1–6**, 2026-09-27). Full suite: **1849 passed, 4 skipped, 0 failed**. **Prompt 7 deferred:** keep `IngredientRegistry` (ontology tests + `verify_ingredient_flow.py`) and the unused `record_resolution_metric` method; rewriting them has no user benefit. Hand-vs-catalog disagreement is `tests/ike2/test_hand_catalog_agreement.py`.
**Companion:** `docs/phase2_gap_analysis.md` § Item 33 · `docs/phase_plan.md` · Items **16** (evaluate cutover closed) · **18+23** (queue/worker closed) · tracker row **33**

---

## 0. How to use this document

Item 33 is **not** “build a second resolver.” Chat and `/api/v1/evaluate-*` already serve IKE-2 only (Item 16 Prompt 7). This spec retires the **remaining** legacy resolve spine that still powers fact-only HTTP endpoints, Redis resolution cache, `lifecycle.py`, and the dead-end `unknown_ingredients` feeder.

Facts in §1 come from three independent evidence rounds — do not re-derive wholesale. Where this document says “identify” or “confirm,” investigate first. Open questions in §7 are **check-ins**, not silent defaults (same discipline as Items 1 / 1.2 / 2).

Keep this at `docs/item33_dual_resolve_engines.md` (this file replaces the thin stub).

---

## 1. Current state (confirmed — act on this)

### 1.1 Two spines still live

| Surface | Engine today | Writes unknowns to |
|---------|--------------|--------------------|
| Chat (`/chat/grocery`) + `/api/v1/evaluate-*` | IKE-2 (`ike2/resolver.resolve` + compliance) | `ike2_unknown_queue` (L5, Items 18+23) |
| `POST /api/v1/resolve-ingredient` | Legacy `CanonicalResolver` → `IngredientRegistry` | `unknown_ingredients` when `log_unknown=True` (default) |
| `GET /api/v1/ingredient/{name}` | Same legacy path | None (`log_unknown=False`) |
| Redis resolution cache | Wired **only** to legacy `canonicalizer` | — |
| Worker enrichment | IKE-2 (`enrich_unknown_batch` → `ike2_*`) | Drains `ike2_unknown_queue` only |
| `core/knowledge/lifecycle.py` | Legacy enum scaffold (`UNKNOWN`…`LOCKED`) | Used by canonicalizer + Redis serializers |
| IKE-2 knowledge trust | DB enum `ike2_knowledge_state` (+ `UNCLASSIFIED` / `DEPRECATED`) | Independent of `lifecycle.py` |

This is the same class of split that caused doc/reality drift before Item 16 — evaluate moved; resolve did not.

### 1.2 Evidence trail (why this is shovel-ready now)

1. **Phase 2 gap analysis (2026-09-17):** `/api/v1/resolve-ingredient` and `GET /ingredient/{name}` still on legacy `CanonicalResolver`; Redis only on that path; `lifecycle.py` delete-after-retirement.
2. **Item 18 investigation (2026-09-23):** same legacy feeders still upsert `unknown_ingredients`; worker no longer drains that table → active dead-end accumulation (test junk `a` / `b` / `zyzzx…` climbing on every suite run).
3. **Items 18+23 closeout:** L5 → `ike2_unknown_queue` → Beat/worker → `ike2_*` works end-to-end. Remaining dual-resolve debt is explicitly this item’s (not Item 16).

### 1.3 What already works (IKE-2 side — preserve)

- **Resolver** (`backend/core/knowledge/ike2/resolver.py`): in-process `ResolutionCache` → L1 truth_anchor → L2 local_ontology → L3 DB alias/disambiguation → synonymy ladder → L5 uncertain (never SAFE).
- **L5 enqueue** (Item 18): fire-and-forget `unknown_queue.record_miss`; verdict-silent; never raises.
- **Evaluate HTTP** (`v1_evaluate.py` / bridge): IKE-2 only; response still `ComplianceVerdict.to_dict()` shape (Item 9 owns rich `assemble(b2b)` later).
- **Worker** (`worker/tasks.py`): drains `ike2_unknown_queue`; no legacy table writes.

### 1.4 What the legacy resolve path still does

| Piece | Path | Notes |
|-------|------|-------|
| HTTP POST resolve | `core/api/v1/routes.py` → `CanonicalResolver.resolve_with_fallback` | Defaults: `try_api=True`, `log_unknown=True` |
| HTTP GET ingredient | same | `try_api` query param; `log_unknown=False` |
| Response schema | `ResolvedIngredientResponse` | `ingredient` dict (`Ingredient.to_dict`), `source_layer`, `confidence_band`, `knowledge_state`, `knowledge_source` from **lifecycle** |
| Registry | `IngredientRegistry` | static + dynamic ontology + optional external API on miss |
| Unknown log | `unknown_log.log_unknown_ingredient` → JSON + `IngredientKnowledgeDB.upsert_unknown_ingredient` | Legacy table only |
| Redis | `core/cache/redis_resolution.py` | Get/set around canonicalizer; serializes `KnowledgeMetadata` / `KnowledgeState` |
| Lifecycle | `core/knowledge/lifecycle.py` | Parallel vocabulary to `ike2_knowledge_state`; **do not unify enums** |
| Metrics | `enrichment_metrics` via canonicalizer | Legacy resolve path only (Item 12 may later move metrics) |

### 1.5 Callers outside HTTP (strangler inventory — Prompt 1 must complete)

Known today (confirm / extend in Prompt 1):

- **Scripts:** `verify_ingredient_flow.py`, `verify_knowledge_flow.py`, `verify_all_health.py`, `add_test_unknowns_and_enrich.py`, `verify_redis_resolution_flow.py`
- **Tests:** `test_redis_resolution_cache.py`, `test_enrichment_registry_guard.py`, `test_compliance_engine.py` (registry helpers), `test_system_scenarios_comprehensive.py`, `test_core_paths.py`, `test_chat_ingredients.py` (partial)
- **Docs:** `backend/docs/EXTERNAL_APIS.md` still describes CanonicalResolver as the enrichment entry

No production chat/evaluate path imports `CanonicalResolver` for verdicts (Item 16).

**Additional confirmations (exploration 2026-09-23):**

- **Frontend** does not call `/resolve-ingredient` or `/api/v1/ingredient/*` — B2C is chat BFF only. External B2B clients of resolve HTTP are **unknown**; Prompt 1 should note that absence of in-repo callers ≠ absence of out-of-repo clients.
- Chat/evaluate already accept `use_api_fallback` for schema compat but **ignore** it (`bridge` / `v1_evaluate`) — same pattern recommended for resolve `try_api` after cutover.
- IKE-2 resolve cache is **in-process only** (`ike2/resolution_cache.py`); Redis is exclusively on the legacy spine.
- `ike2/response.assemble` (`SCHEMA_VERSION = "ike2.v1"`) exists with **no** production HTTP caller — Item **9** owns wiring it; Item 33 must not invent a parallel rich resolve schema.
- Stale docs still describing chat via CanonicalResolver/API: `docs/redis-for-speed-and-ux.md`, parts of `backend/docs/EXTERNAL_APIS.md` (Prompt 6 hygiene list).

### 1.6 What does **not** exist yet

- No IKE-2-backed implementation of `/resolve-ingredient` / `/ingredient/{name}`.
- No response adapter from `ike2.ResolvedIngredient` → `ResolvedIngredientResponse` (shapes differ: group flags vs `Ingredient` dataclass; layer tags vs `static|dynamic|api`).
- No cutover that stops writing `unknown_ingredients` from HTTP/registry.
- No deletion of `lifecycle.py` / Redis-on-legacy / (eventually) `CanonicalResolver` itself.
- No Redis for IKE-2 (and **not** required to close this item — see non-goals).

---

## 2. Purpose of this component

Make **one** resolve spine authoritative for all product surfaces: IKE-2. Retire legacy fact-resolve HTTP, its Redis cache, and `lifecycle.py` together so docs, tests, and discovery writes cannot drift apart again — and so `unknown_ingredients` stops accumulating undrained junk.

---

## 3. Scope

### In scope

- Move (or, if §7 chooses deprecate, remove) HTTP resolve endpoints onto IKE-2.
- Stop legacy `log_unknown` / resolve HTTP from writing `unknown_ingredients` (IKE-2 L5 already owns discovery).
- Retire Redis-on-legacy for resolve once no canonicalizer callers remain on the hot path.
- **Delete** `lifecycle.py` after its last importer is gone (do **not** merge enums into `ike2_knowledge_state`).
- Strangler: inventory → HTTP cutover → feeder cutover → delete scaffolding; scripts/tests updated or deleted in the same prompts that remove their dependencies.
- Tests proving: resolve HTTP no longer touches `unknown_ingredients`; miss path still reaches `ike2_unknown_queue` (via resolver L5); evaluate/chat unchanged; Redis-off path still works for any remaining non-resolve uses until Redis module deleted.

### Explicitly out of scope

- Item **9** B2B auth keys / `assemble(b2b)` / `schema_version` on evaluate (resolve may keep a thin fact schema; rich productization is 9).
- Item **12** Sentry / miss_class productization (carry note only: failed queue writes already logged).
- Adding Redis (or any distributed cache) to IKE-2 — only if/when multi-instance scale exists; **not** part of closing 33.
- Deleting entire `IngredientRegistry` / static ontology loaders in one shot if still used as a **data source** behind IKE-2 Tier 2 local ontology — IKE-2 already has its own stores; do not confuse “delete legacy resolve entrypoint” with “delete ontology JSON.”
- Truncating production `unknown_ingredients` as a migration requirement (ops note in `SUPABASE_TABLES.md` already: safe to truncate).
- Item **29** remote Tier-3 population.
- Changing compliance verdict vocabulary or evaluate response shape.

---

## 4. Target design

### 4.1 Single spine

```
HTTP resolve / GET ingredient
        │
        ▼
ike2.resolver.resolve(atom, region)
        │
        ├─ resolved → map to ResolvedIngredientResponse (adapter)
        └─ uncertain → ingredient=null; L5 already enqueued (Item 18)
```

Evaluate / chat stay on their existing IKE-2 paths — **no** second cutover.

### 4.2 Response adapter (facts only)

Preserve the public field names on `ResolvedIngredientResponse` unless §7 chooses a breaking bump (prefer preserve for Item 9 continuity):

| Response field | Mapping from IKE-2 |
|----------------|--------------------|
| `ingredient` | Group flags → `Ingredient`-compatible dict (or `null` on uncertain). Canonical name from group; aliases optional/empty on miss path. |
| `source_layer` | Map `resolution_layer` / `source` to a stable string set (document the map; do not invent `api` for L5 — APIs are offline). |
| `confidence_band` | From IKE-2 `confidence_band` / trusted (document map to high/medium/low/none). |
| `knowledge_state` | From group `knowledge_state` when resolved; a documented sentinel (e.g. `UNKNOWN` or `UNCLASSIFIED`) when uncertain — **check-in §7**. |
| `knowledge_source` | From IKE-2 `source` / layer tag. |

Do **not** call external APIs on the HTTP resolve hot path. Offline enrichment remains Items 18+23.

### 4.3 Discovery writes

- Resolved miss on IKE-2 already → `ike2_unknown_queue` (Item 18).
- After HTTP cutover: **zero** writes to `unknown_ingredients` from resolve endpoints or from any code path those endpoints still share.
- `IngredientRegistry.log_unknown` / `upsert_unknown_ingredient`: either delete call sites or gate hard-off (prefer delete once registry is no longer on HTTP).

### 4.4 Redis + lifecycle retirement

1. HTTP + scripts no longer import `CanonicalResolver` for product resolve.
2. Remove Redis get/set from canonicalizer (or delete canonicalizer).
3. Delete `redis_resolution.py` if unused; keep compose Redis for Celery only.
4. Delete `lifecycle.py` when no imports remain.
5. Do **not** introduce IKE-2 Redis as a substitute.

### 4.5 `try_api` / `log_unknown` request fields

After cutover these become **compat knobs**, not behavior forks:

- `try_api`: ignored (always local/IKE-2 tiers only). Log at DEBUG if `true` so callers notice. Do not hit USDA/OFF on request.
- `log_unknown`: ignored for legacy table; IKE-2 L5 always records misses (fail-silent). Optionally treat `log_unknown=False` as “skip enqueue” — **check-in §7** (default recommendation: keep L5 enqueue always; telemetry should not be caller-suppressible on B2B resolve).

---

## 5. Safety invariants (non-negotiable)

1. **Evaluate/chat verdicts unchanged** by resolve cutover (no shared mutable global that resolve can poison).
2. **Miss → never SAFE** on resolve response (`ingredient` null / uncertain bands only).
3. **No hot-path external API** on resolve HTTP (Item 2 / IKE-2 design already forbids this).
4. **No write to `unknown_ingredients`** from any code path owned by this item after feeder cutover.
5. **Do not unify** `lifecycle.KnowledgeState` with `ike2_knowledge_state` — delete the former.
6. **Do not demote** LOCKED/VERIFIED groups via resolve (resolve is read-only w.r.t. groups; enqueue only).

---

## 6. Sub-items / work packages

| Package | Intent |
|---------|--------|
| **33.0** | Prompt 1 inventory + open-question check-in (no behavior change) |
| **33.1** | Response adapter + HTTP resolve/GET on IKE-2 |
| **33.2** | Stop legacy unknown feeder (registry/HTTP/scripts) |
| **33.3** | Retire Redis-on-legacy + `lifecycle.py` + dead resolve entrypoints |
| **33.4** | Docs / EXTERNAL_APIS / SUPABASE_TABLES / phase_plan sync |

---

## 7. Open questions — **closed 2026-09-23**

| # | Decision |
|---|----------|
| **Q1** | **Keep + migrate** resolve HTTP onto IKE-2. Fact-only resolve remains a B2B surface (no in-repo frontend callers); distinct from evaluate. |
| **Q2** | **Preserve** `ResolvedIngredientResponse` field names via adapter (same pattern as Item 16 `map_ike2_to_compliance_verdict`). Breaking schema bump waits for Item 9 `schema_version`. |
| **Q3** | Uncertain resolve returns **`knowledge_state=UNCLASSIFIED`** (IKE-2 vocabulary). Do not emit lifecycle `UNKNOWN`. |
| **Q4** | **Always** L5-enqueue on miss; `log_unknown` request field becomes a no-op (documented). Item 18 junk filter still applies. |
| **Q5** | **Kill cleanly** — delete HTTP legacy wiring, Redis-on-legacy resolve cache, and `lifecycle.py` in this item. No zombie public entrypoint (`CanonicalResolver` / registry resolve as product API). Same “delete the thing” discipline as Item 16 Prompt 7. |

`try_api` on resolve HTTP: **ignored** (DEBUG log if `true`), matching evaluate’s already-ignored `use_api_fallback`.

---

## 8. Numbered build prompts for Cursor

**Prompt 1** — Investigate and report (no behavior change): complete the caller inventory for `CanonicalResolver`, `IngredientRegistry.resolve_with_fallback`, `log_unknown_ingredient`, `lifecycle`, `redis_resolution`. Note every test/script that would break if HTTP moves to IKE-2. Diff `ResolvedIngredientResponse` fields against `ike2.ResolvedIngredient` + group flag set; draft the adapter map as a table in this file’s stage log. Confirm current local counts for `unknown_ingredients` vs `ike2_unknown_queue`. §7 Q1–Q5 are **already locked** — do not re-open; inventory only.

**Prompt 2** — Implement response adapter (pure function + unit tests) mapping IKE-2 resolved/uncertain → `ResolvedIngredientResponse` per locked Q2/Q3. No route change yet.

**Prompt 3** — Wire `POST /resolve-ingredient` and `GET /ingredient/{name}` to `ike2.resolver.resolve` + adapter. `try_api` ignored; `log_unknown` per Q4. Tests: no `unknown_ingredients` write; L5 miss increments/inserts `ike2_unknown_queue` (fake client); known Tier-1/2/3 names resolve; evaluate endpoints untouched.

**Prompt 4** — Feeder cutover: remove or hard-disable `upsert_unknown_ingredient` from any remaining resolve-adjacent paths owned by this item; update scripts that called `log_unknown_ingredient` for “enqueue” to either use IKE-2 resolve or queue helpers. Assert suite no longer grows junk keys in `unknown_ingredients` from resolve tests (isolation fixture acceptable if a script still needs legacy for one release — prefer delete).

**Prompt 5** — Retire Redis-on-legacy resolve cache and `lifecycle.py` once imports are gone. Update/delete `test_redis_resolution_cache.py` and `verify_redis_resolution_flow.py`. Compose Redis remains for Celery.

**Prompt 6** — Docs hygiene: `EXTERNAL_APIS.md`, `docs/redis-for-speed-and-ux.md`, `SUPABASE_TABLES.md`, `phase2_gap_analysis.md` §33, `api-v1-and-frontend-endpoints.md`, this stage log, `phase_plan.md`. Mark Item 33 core complete when Prompts 2–5 land and full suite is green.

**Prompt 7** — **Deferred (2026-09-28).** Keep `IngredientRegistry` for the ontology tests and `verify_ingredient_flow.py`, and keep the unused `ingredient_db.record_resolution_metric` method. Deleting them means rewriting working tests for no user benefit.

---

## 9. Keeping this file in sync

Update the stage log at each prompt. Do not start Prompt N+1 until Prompt N is logged. Open questions answered in the stage log with date + decision text.

---

## Stage log

| When | Notes |
|------|-------|
| 2026-09-17 | Stub filed from Phase 2 open-question answer. |
| 2026-09-23 | Items **18+23** closed; remaining debt = HTTP resolve + `log_unknown` → `unknown_ingredients`. |
| 2026-09-23 | **Spec drafted** (this document). Implementation blocked on Prompt 1 inventory + §7 Q1–Q5 check-in. |
| 2026-09-23 | Exploration pass folded in: no frontend resolve callers; `use_api_fallback` already ignored on evaluate; Redis = legacy-only; `assemble(ike2.v1)` = Item 9; stale redis/EXTERNAL_APIS docs listed for Prompt 6. |
| 2026-09-23 | **§7 Q1–Q5 locked** (user): keep+migrate; preserve schema via adapter; uncertain=`UNCLASSIFIED`; always enqueue (`log_unknown` no-op); kill cleanly (no zombie entrypoint). `try_api` ignored like evaluate `use_api_fallback`. Prompt 1 unblocked. |
| 2026-09-24 | **Prompt 1 done** — inventory + adapter draft map + queue counts below. Ready for Prompt 2 (adapter only). No behavior change this prompt. |
| 2026-09-25 | **Prompt 2 done** — `ike2/resolve_response.map_ike2_to_resolved_response` flattens via `seam.to_compliance_input` (BOOL_FLAGS including peanut/tree-nut/fish/shellfish/mustard/celery/lupin/sulphite/enzymes + `nut_source` compat). Uncertain → `ingredient=null`, `knowledge_state=UNCLASSIFIED`, `source_layer=unknown` (never `api`). No route wiring, no enqueue. Tests: `tests/ike2/test_resolve_response.py`. |
| 2026-09-25 | **Prompt 3 done** — `POST /resolve-ingredient` and `GET /ingredient/{name}` call `ike2.resolver.resolve` + adapter. `try_api` logged and ignored (no hot-path API). `log_unknown` ignored; L5 still enqueues `ike2_unknown_queue` (junk keys still skipped). Evaluate routes unchanged. Tests: `tests/ike2/test_resolve_http_ike2.py`. **Pre-existing, not fixed here:** ResolutionCache seed `setdefault` lets E441 (normalizes to `gelatin`, generated catalog `AUTO_CLASSIFIED`) shadow the hand-curated LOCKED gelatin anchor. Lookup-by-`lookup()` is still LOCKED; the cache hit is not. |
| 2026-09-25 | **Prompt 4 done** — `unknown_log.record` enqueues `ike2_unknown_queue` and no longer calls `upsert_unknown_ingredient`. That method now returns False without writing. Scripts `verify_knowledge_flow.py`, `add_test_unknowns_and_enrich.py`, `verify_ingredient_flow.py` comments updated. Tests: `tests/ike2/test_legacy_unknown_feeder.py`. |
| 2026-09-25 | **Cache-seed collision report (no fix).** Three normalized keys: `gelatin` (E441), `bone phosphate` (E542), `disodium inosinate` (E631). E-number JSON is merged first; `seed_tier1` uses `setdefault` on `normalize(alias)`, so the catalog row wins over the later LOCKED hand anchor. Gelatin and disodium inosinate: winner still `animal_origin=True` (same species/cap as the hand row) — Item 34 FAIL still fires; wrong tier only. **Bone phosphate: winner `animal_origin` is absent/false; hand LOCKED row is `animal_origin=True`.** Vegan/vegetarian animal rules will not fire on the cache hit. Same-day exposure, not a Prompt-5 deferral. Recommended fix: seed hand LOCKED/VERIFIED anchors after catalog rows with overwrite, or trust-aware merge (higher knowledge_state replaces). Deterministic order (e-number file, then `_ANCHORS`), not random — the intended L1-wins order is what `setdefault` violates. |
| 2026-09-25 | **Cache-seed fix.** `seed_tier1` keeps the higher `knowledge_state` on a shared normalized key. Uncertainty flags and a missing `verdict_cap` from the lower-trust row are kept. Gelatin stays the hand LOCKED row (already had the same cap). Disodium inosinate stays LOCKED `animal_origin=True` and now also keeps catalog `may_be_from_yeast_or_tapioca` + `verdict_cap=WARN` (hand one-liner had no recorded reason to drop them). Bone phosphate unchanged from the prior merge. Peanut-allergy (no animal trigger) on disodium is WARN, not SAFE; vegan is FAIL. Tests: `tests/ike2/test_resolution_cache_seed_trust.py`. |
| 2026-09-26 | **Catalog checker narrow list adopted.** `verify_e_number_catalog.py` source-ambiguity tokens now include yeast, tapioca, corn, microbial, fermentation, bacterial (plus the old animal/plant/synthetic/poultry/hog). Live hits: E626, E630, E631 only. E441 species note is not a hit. Catalog rows were not edited. CI allows only those three known errors; any other catalog error still fails. **Tracked follow-up (not closed):** nothing scans new hand-vs-catalog disagreements before they share a cache key. Soy lecithin / E322 stays as specified: the named form is one source inside an ambiguous generic code. |
| 2026-09-26 | **L-cysteine / E910 report (no fix).** Hand `_add(["l-cysteine", "cysteine"], ..., animal_origin=True)` has no comment. Copy says "can be derived from animal hair/feathers". `compliance.py` calls that fact blunt and refuses to overlay it onto E910, which stays Depends. Live vegan: `l-cysteine` / `cysteine` / `E920` (normalizes to `l-cysteine`) = NOT_SAFE; `E910` = UNCERTAIN. Recommended content fix, not a cache fix: the hand anchor should carry the catalog hedge (`may_be_synthetic_or_from_plant_fermentation`, `traditionally_from_poultry_feathers_or_hog_hair`, `verdict_cap=WARN`) and not assert unconditional `animal_origin`, so the name and the E-code converge. |
| 2026-09-27 | **L-cysteine hand anchor updated.** Dropped unconditional `animal_origin`. Anchor now carries the catalog hedge and `verdict_cap=WARN`. `l-cysteine`, `cysteine`, `E920`, and `E910` share one vegan verdict (WARN, external UNCERTAIN). Test: `tests/ike2/test_cysteine_labels.py`. Soy lecithin untouched. |
| 2026-09-27 | **Prompt 5 done.** Deleted `core/cache/redis_resolution.py`, `core/knowledge/lifecycle.py`, and `core/knowledge/canonicalizer.py` (sole remaining importers of the first two; not on the product path). Deleted `tests/test_redis_resolution_cache.py` and `scripts/verify_redis_resolution_flow.py`. `verify_all_health.py` and `verify_knowledge_flow.py` now call `ike2.resolver.resolve`. Compose Redis stays for Celery. **Still present, not a product entry:** `IngredientRegistry` used by ontology unit tests and `scripts/verify_ingredient_flow.py`. Prompt 7 can delete or defer that. |
| 2026-09-27 | **Prompt 6 done (core complete).** Full suite **1849 passed, 4 skipped, 0 failed** (1832-passed baseline + 17 net). No import errors from the deleted modules. `unknown_ingredients` unchanged across the run (`a` 36, `b` 18, `zyzzx unknown starch q99` 18, `wheat flour` 36; last_seen still 2026-09-23). `enrichment_metrics` has 0 rows; the only writer was `canonicalizer._emit_resolution_metric`, and nothing reads the table. Item 12 note recorded. Docs updated: `EXTERNAL_APIS.md`, `redis-for-speed-and-ux.md`, `SUPABASE_TABLES.md`, `phase2_gap_analysis.md`, `api-v1-and-frontend-endpoints.md`, this file, `phase_plan.md`. |
| 2026-09-28 | **Prompt 7 deferred.** Keep `IngredientRegistry` (ontology tests + `verify_ingredient_flow.py`) and the unused `record_resolution_metric` method. |

### Prompt 1 findings (2026-09-24)

#### 1. Caller inventory

**Product HTTP (must move in Prompt 3)**

| Site | Calls | Side effects today |
|------|-------|--------------------|
| `POST /api/v1/resolve-ingredient` (`routes.py`) | `CanonicalResolver.resolve_with_fallback` | `try_api=True` default → sync API; `log_unknown=True` → `unknown_ingredients` |
| `GET /api/v1/ingredient/{name}` | same | `log_unknown=False`; optional `try_api` |

**CanonicalResolver stack (delete with Prompt 5 after HTTP cutover)**

| Module | Role |
|--------|------|
| `core/knowledge/canonicalizer.py` | In-process cache → **Redis** → **legacy** `ingredient_aliases`/`ingredient_groups` (`_resolve_via_db`) → `IngredientRegistry` |
| `core/cache/redis_resolution.py` | Redis get/set; serializes `lifecycle.KnowledgeState` |
| `core/cache/__init__.py` | Re-exports Redis helpers |
| `core/knowledge/lifecycle.py` | Enum + `KnowledgeMetadata` — **only** imported by canonicalizer + redis_resolution (+ their tests) |

**Surprise — third knowledge store on legacy HTTP:** `CanonicalResolver._resolve_via_db` reads **legacy** Supabase tables (`ingredient_aliases` → `ingredients` → `ingredient_groups`), **not** `ike2_*`. Migrating resolve HTTP to IKE-2 removes this path from the product surface (desired). Chat/evaluate never used it.

**`log_unknown_ingredient` → `unknown_ingredients` writers**

| Site | Notes |
|------|-------|
| `IngredientRegistry.resolve_with_fallback` (`log_unknown=True`) | Production feeder when HTTP resolve uses it |
| `unknown_log.record` | Always tries `upsert_unknown_ingredient` when DB enabled |
| `scripts/verify_knowledge_flow.py` | Explicit call |
| `scripts/add_test_unknowns_and_enrich.py` | Explicit call |
| `scripts/verify_ingredient_flow.py` | Via `resolve_with_fallback(..., log_unknown=True)` |
| `tests/test_compliance_engine.py` | `zyzzx unknown starch q99` + `log_unknown=True` — **confirmed pollution source** for junk pattern |

**Scripts that break / need rewrite when CanonicalResolver dies**

| Script | Action in later prompts |
|--------|-------------------------|
| `verify_all_health.py` | Switch `bajra` check to `ike2.resolver.resolve` |
| `verify_knowledge_flow.py` | Point at IKE-2 resolve / queue; drop legacy upsert claim |
| `verify_ingredient_flow.py` | Same |
| `verify_redis_resolution_flow.py` | **Delete** with Redis-on-legacy (Prompt 5) |
| `add_test_unknowns_and_enrich.py` | Retarget to `ike2_unknown_queue` or delete |

**Tests that assert legacy resolve behavior**

| Test | Impact |
|------|--------|
| `test_redis_resolution_cache.py` | Delete/rewrite with Prompt 5 |
| `test_enrichment_registry_guard.py` | Uses `resolve_with_fallback`; rewrite or drop sync-API claims |
| `test_compliance_engine.py` | Static `reg.resolve` can stay until Prompt 7; **`log_unknown=True` API test must stop writing legacy** (Prompt 4) |
| `test_system_scenarios_comprehensive.py` | `reg.resolve` for E-number merge — ontology loader only |
| `test_core_paths.py` | Registry path load |
| `test_chat_ingredients.py` | `__new__` CanonicalResolver stub — rewrite if it touches resolve HTTP |

**Keep vs kill (aligned with Q5)**

- **Kill (this item):** HTTP wiring to CanonicalResolver; Redis resolve cache; `lifecycle.py`; product use of `resolve_with_fallback` / `log_unknown` → legacy table.
- **May remain until Prompt 7:** `Ingredient` dataclass, `IngredientRegistry.resolve` / static ontology load used by non-HTTP tests — **not** a product entrypoint. If still present after Prompt 5 with no callers, Prompt 7 deletes or files a one-line deferral.

**Non-importers (safe):** chat, `bridge._run_ike2_compliance`, `v1_evaluate`, worker enrichment — already IKE-2.

#### 2. Queue counts (local DB, 2026-09-24)

| Table | Rows | Detail |
|-------|-----:|--------|
| `unknown_ingredients` | **4** (all unresolved) | `wheat flour` 36, `a` 36, `zyzzx…` 18, `b` 18 — sum frequency **108**. Still climbing from test pollution; nothing drains. |
| `ike2_unknown_queue` | **1** | `wheat flour` freq 34, **`status=resolved`** (live 18+23 closeout). Pending count **0**. |

#### 3. Shape diff — adapter draft map (Prompt 2 implements)

**Top-level `ResolvedIngredientResponse` (preserve field names — Q2)**

| Field | Legacy today | IKE-2 source → adapter |
|-------|--------------|------------------------|
| `ingredient` | `Ingredient.to_dict()` or `null` | See flag map below; `null` when `status != "resolved"` |
| `source_layer` | `static` \| `dynamic` \| `api` \| `unknown` | `L1_truth_anchor` → `static`; `L2_local_ontology` → `static`; `L3_db_*` → `dynamic`; `L5_unknown_queue` / ambiguous / db_error → `unknown`. **Never emit `api`** (hot-path APIs retired). |
| `confidence_band` | `high` \| `medium` \| `low` \| null | `exact`/`high` → `high`; `none` / uncertain → `null` |
| `knowledge_state` | lifecycle enum string | Resolved: group `knowledge_state` as-is (`LOCKED`…`DISCOVERED`…). Uncertain: **`UNCLASSIFIED`** (Q3). |
| `knowledge_source` | e.g. `static_ontology`, `external_api` | Pass through IKE-2 `source` (`truth_anchor`, `local_ontology`, `db`, `unknown_queue`). |

**`ingredient` dict — lossy if naïvely using `Ingredient.to_dict()` only**

| Concern | Detail |
|---------|--------|
| IKE-2 has, `Ingredient` lacks | `peanut_source`, `tree_nut_source`, `fish_source`, `shellfish_source`, `mustard_source`, `celery_source`, `lupin_source`, `sulphite_source`, `enzyme_animal_source`, `enzyme_microbial_source`, `alcohol_role`, `verdict_cap`, … |
| `Ingredient` has, IKE-2 splits | `nut_source: Optional[str]` vs peanut/tree_nut booleans |
| Group shapes | `TruthAnchorFact` → `.flags` dict; DB `GroupRow` → flat attrs; local ontology → same as seam |

**Adapter recommendation for Prompt 2 (not a new open question — implements Q2 safely):**

1. Flatten group the same way `seam.to_compliance_input` does (reuse or call a shared helper — prefer reuse to avoid a second flag path).
2. Build `ingredient` as a **dict** (schema already `Dict[str, Any]`): include all IKE-2 boolean flags present on the group/flags map, plus `id` (group id or canonical_name), `canonical_name`, `aliases` (empty OK), `uncertainty_flags`, `animal_species`, `alcohol_content`, `regions` if present.
3. For legacy clients: if `peanut_source` and/or `tree_nut_source`, also set `nut_source` to a compat string (`"peanut"`, `"tree_nut"`, or `"peanut,tree_nut"`).
4. Do **not** call `Ingredient.to_dict()` alone — it would drop allergen specificity (false under-flagging on the fact surface).
5. Uncertain: `ingredient=null`; still L5-enqueues inside `resolve()` (Q4); adapter does not write any queue itself.

**Read-only invariant (§5):** adapter + resolve HTTP perform **no** group INSERT/UPDATE. Enqueue only.

#### 4. Prompt 2 readiness

- Q1–Q5 locked; inventory complete; adapter map drafted.
- No code changes in Prompt 1.
- **Next:** Prompt 2 — pure `map_ike2_to_resolved_response` (name TBD) + unit tests; no route wiring yet.

---

## 10. Success criteria

- [x] `/api/v1/resolve-ingredient` and `/api/v1/ingredient/{name}` resolve via IKE-2 (or are removed per Q1).
- [x] Zero product-path writes to `unknown_ingredients`.
- [x] L5 misses from resolve HTTP still land on `ike2_unknown_queue`.
- [x] `lifecycle.py` deleted; no Redis resolve cache on legacy.
- [x] Evaluate/chat + IKE-2 goldens unchanged.
- [x] Docs no longer claim CanonicalResolver is the enrichment/resolve entry for `/api/v1`.
- [x] Full suite green; no new undrained legacy junk from resolve tests.
