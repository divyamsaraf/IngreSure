# Supabase Tables

> **Current state:** Menu/restaurant tables (`menu_items`, `verified_items`, `verification_logs`, `item_ingredients`, `tag_history`, `embeddings`, `restaurant_submissions`) have been **dropped** (migration `20260306100000`). Living schema = legacy knowledge tables + `users` + `request_history` + full `ike2_*` / `ike2_staging` set (migrations `20260409120000`, `20260616000000`+). See `docs/SUPABASE_AFTER_RESTAURANT_REMOVAL.md` and `docs/system_state_audit.md`.

## Verification

From repo root:

```bash
python backend/scripts/verify_supabase.py
```

This checks connectivity, lists public tables and their RLS status, and summarizes which tables are required vs optional.

## Tables Overview

| Table | Purpose | Required? | RLS |
|-------|---------|-----------|-----|
| **Knowledge base (legacy)** | | | |
| `ingredient_groups` | Canonical ingredient identity (origin, flags) | Yes (legacy path / enrichment) | ON, backend-only |
| `ingredients` | Names/strings that map to a group | Yes | ON, backend-only |
| `ingredient_aliases` | Normalized alias → ingredient → group | Yes | ON, backend-only |
| `unknown_ingredients` | Discovery queue (worker enrichment today) | Yes (until Item 18 consolidation) | ON, backend-only |
| `enrichment_metrics` | Coverage/resolution metrics per day | No (analytics only) | ON, backend-only |
| **App** | | | |
| `users` | Auth-linked profiles (`diet_type`, `allergies`, `preferences`) | Optional (auth / `USE_PROFILE_DB`) | ON, own row |
| `request_history` | Write-only HTTP/chat analytics from FastAPI | No (ops) | ON, no client policies |
| **IKE-2 (public)** | | | |
| `ike2_ingredient_groups` | IKE-2 canonical groups + flags + knowledge_state | Yes (IKE-2 primary) | ON, backend-only |
| `ike2_ingredients` | Normalized ingredient rows under a group | Yes | ON, backend-only |
| `ike2_aliases` | Alias → ingredient (region/type/confidence) | Yes | ON, backend-only |
| `ike2_alias_disambiguation` | Ambiguous alias context → ingredient | Yes | ON, backend-only |
| `ike2_restriction_rules` | Restriction rules (category/field/action) | Yes | ON, backend-only |
| `ike2_resolution_cache` | Optional SQL resolution audit cache | No (hot path is in-process) | ON, backend-only |
| `ike2_unknown_queue` | IKE-2 discovery queue (schema ready; writes not yet primary) | Yes (target for Item 18) | ON, backend-only |
| `ike2_shadow_diffs` | Legacy vs IKE-2 observational diffs | Yes (cutover / Item 16) | ON, backend-only |
| `ike2_group_merges` | Group merge / rollback snapshots | No (ops) | ON, backend-only |
| **IKE-2 staging schema** | | | |
| `ike2_staging.ingredient_groups` | Raw bulk-inject staging (no UNIQUE/CHECK) | No (ETL) | n/a (non-public) |
| `ike2_staging.stg_rejects` | Reject quarantine for failed staging rows | No (ETL) | n/a (non-public) |

**View:** `public.ike2_v_alias_resolution` — alias → active ingredient → non-DEPRECATED group.

**Enum:** `ike2_knowledge_state` = `UNCLASSIFIED | DISCOVERED | AUTO_CLASSIFIED | VERIFIED | LOCKED | DEPRECATED`.

**Dropped (migration 20260306100000):** `menu_items`, `item_ingredients`, `tag_history`, `verification_logs`, `restaurant_submissions`, `verified_items`, `embeddings`, and `search_menu_items()`.

## Tables That Can Be Removed or Disabled

- **`enrichment_metrics`** – Optional. Only used for coverage analytics. Safe to drop if you do not run metrics aggregation.
- **`ike2_resolution_cache`** – Optional; runtime resolution cache is in-process.
- **`ike2_group_merges`** – Optional ops table until merge tooling is active.

## RLS (Row Level Security)

Migration `20260306000000_enable_rls.sql` turns on RLS for legacy public tables; `20260616000000_ike2_schema.sql` enables RLS on IKE-2 public tables with no anon policies (service_role only).

- **Backend** uses `SUPABASE_SERVICE_ROLE_KEY`, which **bypasses RLS** – all operations continue to work.
- **Knowledge / IKE-2 tables** have **no policies** for anon/authenticated, so only the backend (service role) can read/write.
- **`users`** has policies so authenticated users can access only their own row.
- **`request_history`** is write-oriented from the API; no client policies.

Apply the migration:

```bash
supabase db reset   # local, applies all migrations
# or
supabase db push    # remote, pushes new migrations
```

## Unknown Ingredients → Knowledge Base Flow

1. **User searches** an ingredient (e.g. in chat or scan). The resolver does not find it in the static/dynamic ontology.
2. **`log_unknown_ingredient()`** is called (from `ingredient_registry.resolve_with_fallback` when `log_unknown=True`). It:
   - Updates the in-memory/JSON unknown log.
   - If the knowledge DB is enabled, calls **`IngredientKnowledgeDB.upsert_unknown_ingredient()`**.
3. **`upsert_unknown_ingredient()`** writes to `unknown_ingredients` with:
   - `normalized_key`, `raw_inputs` (list of raw strings), `frequency`, `last_seen`, `restriction_ids_sample`, `profile_context_sample`.
   - If a row exists for `normalized_key`, it increments frequency, appends to `raw_inputs`, and updates `last_seen` and samples.
4. **Worker** (`enrich_unknown_batch` task or `run_enrich_unknown_once.py`) reads rows where `resolved = false` and `frequency >= min_frequency`, calls external APIs to resolve the ingredient, then:
   - On success: **`upsert_from_enrichment()`** inserts/updates `ingredient_groups`, `ingredients`, and `ingredient_aliases`; updates `unknown_ingredients` with `resolved = true`, `resolved_group_id`, `resolution_source`, `resolution_attempts`, `last_attempt_at`.
   - On failure or low confidence: updates `unknown_ingredients` with `resolution_attempts` and `last_attempt_at` only (so the row is ready for retries and traceability).

> **Note (Item 18):** IKE-2 also defines `ike2_unknown_queue`, but the active enrichment path today still uses legacy `unknown_ingredients` exclusively. Consolidation plan is tracked separately.

Saved format in `unknown_ingredients` matches the schema and is sufficient to update the knowledge base: the worker uses `normalized_key` and `raw_inputs` for context, and after enrichment the same tables that the resolver uses (`ingredient_aliases` → `ingredients` → `ingredient_groups`) are updated so future searches resolve the ingredient.
